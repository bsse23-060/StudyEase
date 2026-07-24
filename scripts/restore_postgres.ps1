param([Parameter(Mandatory=$true)][Alias("Input")][string]$BackupFile, [string]$Database = "studyease_restore")
$ErrorActionPreference = "Stop"
if (!(Test-Path -LiteralPath $BackupFile)) { throw "Backup file does not exist: $BackupFile" }
if ($Database -notmatch '^[a-zA-Z0-9_]+$') { throw "Unsafe database name." }
$container = (docker compose ps -q postgres).Trim()
if (!$container) { throw "PostgreSQL Compose container is not running." }
$exists = docker exec $container psql --username=studyease --dbname=postgres --tuples-only --no-align --command="SELECT 1 FROM pg_database WHERE datname='$Database';"
if ($exists -and ($exists -join "").Trim() -eq "1") { throw "Refusing to overwrite existing database: $Database" }
$temporary = "/tmp/studyease-restore.dump"
try {
    docker cp ([System.IO.Path]::GetFullPath($BackupFile)) "${container}:${temporary}"
    if ($LASTEXITCODE -ne 0) { throw "docker cp failed." }
    docker exec $container createdb --username=studyease $Database
    if ($LASTEXITCODE -ne 0) { throw "createdb failed." }
    docker exec $container pg_restore --no-owner --exit-on-error --username=studyease --dbname=$Database $temporary
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed." }
} finally {
    docker exec $container rm -f $temporary | Out-Null
}
docker exec $container psql --username=studyease --dbname=$Database --command="SELECT COUNT(*) FROM django_migrations;"
Write-Host "Restore validation completed in isolated database $Database. Drop it manually after review."
