param([string]$Bucket = "studyease-private", [string]$OutputRoot = ".\backups\objects", [string]$Endpoint = "http://minio:9000")
$ErrorActionPreference = "Stop"
if (!$env:STUDYEASE_MINIO_ACCESS_KEY -or !$env:STUDYEASE_MINIO_SECRET_KEY) { throw "Set STUDYEASE_MINIO_ACCESS_KEY and STUDYEASE_MINIO_SECRET_KEY." }
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = [System.IO.Path]::GetFullPath((Join-Path $OutputRoot $timestamp))
if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite $destination" }
New-Item -ItemType Directory -Path $destination | Out-Null
$hostUrl = $Endpoint -replace '^http://', "http://$($env:STUDYEASE_MINIO_ACCESS_KEY):$($env:STUDYEASE_MINIO_SECRET_KEY)@" -replace '^https://', "https://$($env:STUDYEASE_MINIO_ACCESS_KEY):$($env:STUDYEASE_MINIO_SECRET_KEY)@"
docker run --rm --network studyease_default -e MC_HOST_source="$hostUrl" -v "${destination}:/backup" minio/mc:RELEASE.2025-04-16T18-13-26Z mirror --preserve "source/$Bucket" /backup
if ($LASTEXITCODE -ne 0) { throw "MinIO backup failed." }
docker run --rm -v "${destination}:/backup" alpine:3.21 sh -c "cd /backup && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS"
if ($LASTEXITCODE -ne 0) { throw "Checksum inventory failed." }
Write-Host "Object backup written to $destination"
