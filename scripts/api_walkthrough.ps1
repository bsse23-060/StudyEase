param([string]$BaseUrl = "http://127.0.0.1:8000")
$ErrorActionPreference = "Stop"

function Invoke-JsonPost($Path, $Body, $Token = $null) {
    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    $json = $Body | ConvertTo-Json -Depth 8 -Compress
    try { return Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -Headers $headers -ContentType "application/json" -Body $json }
    catch { throw "POST $Path failed: $($_.Exception.Message) $($_.ErrorDetails.Message)" }
}
function Invoke-JsonGet($Path, $Token) {
    try { return Invoke-RestMethod -Method Get -Uri "$BaseUrl$Path" -Headers @{Authorization="Bearer $Token"} }
    catch { throw "GET $Path failed: $($_.Exception.Message) $($_.ErrorDetails.Message)" }
}

Write-Host "Student login and journey"
$studentAuth = Invoke-JsonPost "/api/v1/auth/token/" @{email="student1@studyease.local"; password="StudyEaseDemo123!"}
$student = $studentAuth.access
$courses = Invoke-JsonGet "/api/v1/courses/" $student
$course = $courses.results | Where-Object slug -eq "python-foundations" | Select-Object -First 1
if (-not $course) { throw "Seeded python-foundations course was not returned." }
$courseDetail = Invoke-JsonGet "/api/v1/courses/$($course.id)/" $student
$module = $courseDetail.modules[0]
$lesson = $module.lessons[0]
$question = $lesson.questions[0]
$attempt = Invoke-JsonPost "/api/v1/attempts/" @{question=$question.id; answer=1; seconds_spent=10} $student
$roadmap = Invoke-JsonGet "/api/v1/roadmap-steps/" $student
$decks = Invoke-JsonGet "/api/v1/flashcard-decks/" $student
$cardSuffix = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$card = Invoke-JsonPost "/api/v1/flashcards/" @{deck=$decks.results[0].id; question="What is mutability? $cardSuffix"; answer="The ability to change an object"} $student
$review = Invoke-JsonPost "/api/v1/flashcard-decks/$($decks.results[0].id)/cards/$($card.id)/review/" @{quality=4} $student
$routine = Invoke-JsonPost "/api/v1/routines/" @{name="API walkthrough routine"; preferences=@{break_style="pomodoro"}} $student
$conversation = Invoke-JsonPost "/api/v1/conversations/" @{title="API walkthrough chat"; course=$course.id} $student
$seededConversations = Invoke-JsonGet "/api/v1/conversations/?search=Lists%20help" $student
Write-Host "Student attempt correct: $($attempt.is_correct); roadmap items: $($roadmap.count); card interval: $($review.interval_days)"

Write-Host "Instructor authoring and ownership checks"
$teacherAuth = Invoke-JsonPost "/api/v1/auth/token/" @{email="instructor1@studyease.local"; password="StudyEaseDemo123!"}
$teacher = $teacherAuth.access
$suffix = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$newCourse = Invoke-JsonPost "/api/v1/courses/" @{slug="walkthrough-api-$suffix"; title="Walkthrough API"; description="Created by the validation script"; is_published=$true} $teacher
$newModule = Invoke-JsonPost "/api/v1/modules/" @{course=$newCourse.id; title="HTTP"; position=1} $teacher
$newLesson = Invoke-JsonPost "/api/v1/lessons/" @{module=$newModule.id; title="GET requests"; kind="quiz"; position=1} $teacher
$newConcept = Invoke-JsonPost "/api/v1/concepts/" @{slug="walkthrough-http-$suffix"; name="HTTP"; lessons=@($newLesson.id)} $teacher
$newQuestion = Invoke-JsonPost "/api/v1/questions/" @{lesson=$newLesson.id; concept=$newConcept.id; kind="multiple_choice"; prompt="Which method retrieves data?"; options=@("GET", "DELETE"); correct_answer=0} $teacher
$students = Invoke-JsonGet "/api/v1/users/" $teacher
$otherCourse = $courses.results | Where-Object slug -eq "web-foundations" | Select-Object -First 1
$forbiddenStatus = 0
try { Invoke-WebRequest -UseBasicParsing -Method Patch -Uri "$BaseUrl/api/v1/courses/$($otherCourse.id)/" -Headers @{Authorization="Bearer $teacher"} -ContentType "application/json" -Body '{"title":"Forbidden change"}' | Out-Null; $forbiddenStatus = 200 }
catch { $forbiddenStatus = [int]$_.Exception.Response.StatusCode }
Write-Host "Created question $($newQuestion.id); visible enrolled students: $($students.count); cross-instructor update HTTP status: $forbiddenStatus (expected 403)"
