param([string]$BaseUrl = "http://localhost:8080")
$ErrorActionPreference = "Stop"
$live = Invoke-RestMethod "$BaseUrl/health/live/"
if ($live.status -ne "ok") { throw "API liveness failed." }
$ready = Invoke-WebRequest "$BaseUrl/health/ready/" -UseBasicParsing
if ($ready.StatusCode -ne 200) { throw "API readiness failed." }
$front = Invoke-WebRequest "$BaseUrl/" -UseBasicParsing
if ($front.StatusCode -ne 200 -or $front.Content -notmatch "studyEase") { throw "Frontend smoke check failed." }
Write-Host "Public liveness, readiness, and frontend smoke checks passed. Run scripts/api_walkthrough.ps1 and scripts/rag_walkthrough.ps1 for authenticated deterministic journeys."
