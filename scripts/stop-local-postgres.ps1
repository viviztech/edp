param(
    [string]$PostgresBin = "C:\Program Files\PostgreSQL\17\bin"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$data = Join-Path $root ".local\postgres17\data"
$pgCtl = Join-Path $PostgresBin "pg_ctl.exe"

if (-not (Test-Path -LiteralPath (Join-Path $data "PG_VERSION"))) {
    throw "Local cluster is not initialized at $data"
}
& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Output "EDP PostgreSQL is already stopped."
    exit 0
}
& $pgCtl stop -D $data -m fast -w
if ($LASTEXITCODE -ne 0) {
    throw "Unable to stop EDP PostgreSQL."
}
