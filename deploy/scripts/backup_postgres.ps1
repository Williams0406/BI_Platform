param(
    [string]$BackupDir = ".\backups"
)

$ErrorActionPreference = "Stop"
if (-not $env:DB_NAME) { throw "DB_NAME required" }
if (-not $env:DB_USER) { throw "DB_USER required" }

$hostName = if ($env:DB_HOST) { $env:DB_HOST } else { "127.0.0.1" }
$port = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$out = Join-Path $BackupDir "$($env:DB_NAME)_$stamp.dump"

& pg_dump --format=custom --no-owner --host=$hostName --port=$port --username=$env:DB_USER --file=$out $env:DB_NAME
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }

Get-FileHash -Algorithm SHA256 $out | Format-List | Out-File "$out.sha256"
Write-Output $out
