param([int]$Count = 25, [string]$Output = ".\load\results\tokens.json")
$ErrorActionPreference = "Stop"
$directory = Split-Path -Parent $Output
if ($directory) { New-Item -ItemType Directory -Force -Path $directory | Out-Null }
$json = docker compose exec -T api python manage.py generate_load_tokens --count $Count
if ($LASTEXITCODE -ne 0) { throw "Token fixture generation failed." }
[System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($Output), ($json | Select-Object -Last 1), [System.Text.UTF8Encoding]::new($false))
Write-Host "Created $Count short-lived local load tokens in ignored output $Output."
