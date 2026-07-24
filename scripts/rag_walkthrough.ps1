param([string]$BaseUrl = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"

function Post-Json($Path, $Body, $Token) {
    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    return Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -Headers $headers -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 8 -Compress)
}
function Get-Json($Path, $Token) { return Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers @{Authorization="Bearer $Token"} }
function Upload-Document($Path, $Title, $CourseId, $Token) {
    Add-Type -AssemblyName System.Net.Http
    $client = [System.Net.Http.HttpClient]::new()
    $client.DefaultRequestHeaders.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new("Bearer", $Token)
    $form = [System.Net.Http.MultipartFormDataContent]::new()
    $form.Add([System.Net.Http.StringContent]::new($Title), "title")
    $form.Add([System.Net.Http.StringContent]::new([string]$CourseId), "course")
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $filePart = [System.Net.Http.ByteArrayContent]::new($bytes)
    $filePart.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::new("text/plain")
    $form.Add($filePart, "file", "dictionaries.txt")
    try {
        $httpResponse = $client.PostAsync("$BaseUrl/api/v1/documents/", $form).GetAwaiter().GetResult()
        $body = $httpResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $httpResponse.IsSuccessStatusCode) { throw "Upload failed ($([int]$httpResponse.StatusCode)): $body" }
        return $body | ConvertFrom-Json
    } finally { $form.Dispose(); $client.Dispose() }
}

$teacher = (Post-Json "/api/v1/auth/token/" @{email="instructor1@studyease.local"; password="StudyEaseDemo123!"} $null).access
$student = (Post-Json "/api/v1/auth/token/" @{email="student1@studyease.local"; password="StudyEaseDemo123!"} $null).access
$student2 = (Post-Json "/api/v1/auth/token/" @{email="student2@studyease.local"; password="StudyEaseDemo123!"} $null).access
$courses = Get-Json "/api/v1/courses/?search=Python%20Foundations" $teacher
$course = $courses.results[0]

$tempFile = New-TemporaryFile
try {
    $suffix = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Set-Content -LiteralPath $tempFile.FullName -Encoding utf8 -Value "Python dictionaries store key-value pairs. Dictionary keys must be hashable. Values may be any Python object. Demo run $suffix."
    $upload = Upload-Document $tempFile.FullName "Dictionary Notes $suffix" $course.id $teacher
    Write-Host "Uploaded document $($upload.id), initial status $($upload.status)"
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        $state = Get-Json "/api/v1/documents/$($upload.id)/processing_status/" $teacher
        if ($state.status -in @("ready", "failed")) { break }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Processing status: $($state.status); chunks: $($state.chunk_count)"

    $conversation = Post-Json "/api/v1/conversations/" @{title="Dictionary RAG demo"; course=$course.id} $student
    $answer = Post-Json "/api/v1/conversations/$($conversation.id)/ask/" @{question="What constraints apply to dictionary keys?"; document_ids=@($upload.id)} $student
    Write-Host "Answer: $($answer.content)"
    Write-Host "Citations:"
    $answer.citations | Format-Table chunk, document_title, page, quote, score

    $personalConversation = Post-Json "/api/v1/conversations/" @{title="Unauthorised test"} $student2
    try {
        $null = Post-Json "/api/v1/conversations/$($personalConversation.id)/ask/" @{question="Read the private document"; document_ids=@($upload.id)} $student2
        $unauthorisedStatus = 200
    } catch { $unauthorisedStatus = [int]$_.Exception.Response.StatusCode }
    Write-Host "Unauthorised retrieval HTTP status: $unauthorisedStatus (expected 400)"

    $failed = Get-Json "/api/v1/documents/?status=failed" $teacher
    if ($failed.count -gt 0) {
        $retry = Post-Json "/api/v1/documents/$($failed.results[0].id)/retry/" @{} $teacher
        Start-Sleep -Milliseconds 250
        $retryState = Get-Json "/api/v1/documents/$($retry.id)/processing_status/" $teacher
        Write-Host "Retried failed demo document $($retry.id); API accepted $($retry.status), current status $($retryState.status)"
    }
} finally {
    Remove-Item -LiteralPath $tempFile.FullName -Force -ErrorAction SilentlyContinue
}
