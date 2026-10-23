param(
    [string]$PostgresBin = "",
    [int]$Port = 55432
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $PostgresBin) {
    $PostgresBin = Join-Path $root ".tool-cache\postgresql17\pgsql\bin"
    if (-not (Test-Path -LiteralPath (Join-Path $PostgresBin "pg_ctl.exe"))) {
        $PostgresBin = "C:\Program Files\PostgreSQL\17\bin"
    }
}
$data = Join-Path $root ".local\postgres17\data"
$log = Join-Path $root ".local\postgres17\postgres.log"
$pgCtl = Join-Path $PostgresBin "pg_ctl.exe"

if (-not (Test-Path -LiteralPath (Join-Path $data "PG_VERSION"))) {
    throw "Local cluster is not initialized at $data"
}
& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Output "EDP PostgreSQL is already running on its configured port."
    exit 0
}
& $pgCtl start -D $data -l $log -o "-p $Port -h 127.0.0.1" -w
if ($LASTEXITCODE -ne 0) {
    throw "Unable to start EDP PostgreSQL."
}
