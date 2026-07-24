param([Parameter(Mandatory=$true)][Alias("Input")][string]$BackupDirectory, [Parameter(Mandatory=$true)][string]$TargetBucket, [string]$Endpoint = "http://minio:9000")
$ErrorActionPreference = "Stop"
if ($TargetBucket -notmatch '^[a-z0-9][a-z0-9.-]+$') { throw "Unsafe target bucket name." }
if (!(Test-Path -LiteralPath $BackupDirectory)) { throw "Backup directory does not exist." }
if (!$env:STUDYEASE_MINIO_ACCESS_KEY -or !$env:STUDYEASE_MINIO_SECRET_KEY) { throw "Set STUDYEASE_MINIO_ACCESS_KEY and STUDYEASE_MINIO_SECRET_KEY." }
$source = [System.IO.Path]::GetFullPath($BackupDirectory)
docker run --rm -v "${source}:/backup:ro" alpine:3.21 sh -c "cd /backup && sha256sum -c SHA256SUMS"
if ($LASTEXITCODE -ne 0) { throw "Local checksum verification failed." }
$hostUrl = $Endpoint -replace '^http://', "http://$($env:STUDYEASE_MINIO_ACCESS_KEY):$($env:STUDYEASE_MINIO_SECRET_KEY)@" -replace '^https://', "https://$($env:STUDYEASE_MINIO_ACCESS_KEY):$($env:STUDYEASE_MINIO_SECRET_KEY)@"
docker run --rm --network studyease_default --entrypoint sh -e MC_HOST_target="$hostUrl" -v "${source}:/backup:ro" minio/mc:RELEASE.2025-04-16T18-13-26Z -c "mc mb --ignore-existing target/$TargetBucket && mc anonymous set none target/$TargetBucket && mc mirror --preserve --exclude SHA256SUMS /backup target/$TargetBucket"
if ($LASTEXITCODE -ne 0) { throw "MinIO restore failed." }
Write-Host "Object restore completed into isolated bucket $TargetBucket"
