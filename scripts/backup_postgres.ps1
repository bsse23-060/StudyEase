param([string]$Output = "")
$ErrorActionPreference = "Stop"
if (!$Output) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $Output = ".\backups\studyease-$timestamp.dump"
}
$Output = [System.IO.Path]::GetFullPath($Output)
if (Test-Path -LiteralPath $Output) { throw "Refusing to overwrite existing backup: $Output" }
$directory = Split-Path -Parent $Output
if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
$container = (docker compose ps -q postgres).Trim()
if (!$container) { throw "PostgreSQL Compose container is not running." }
$temporary = "/tmp/studyease-backup.dump"
try {
    docker exec $container pg_dump --format=custom --no-owner --username=studyease --dbname=studyease --file=$temporary
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed." }
    docker cp "${container}:${temporary}" $Output
    if ($LASTEXITCODE -ne 0) { throw "docker cp failed." }
} finally {
    docker exec $container rm -f $temporary | Out-Null
}
if (!(Test-Path -LiteralPath $Output) -or (Get-Item -LiteralPath $Output).Length -eq 0) { throw "Backup was not created." }
Write-Host "Backup written to $Output. It is not verified until restored and tested."
