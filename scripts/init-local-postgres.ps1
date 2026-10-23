param(
    [string]$PostgresBin = "",
    [ValidateRange(1024, 65535)]
    [int]$Port = 55432
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$clusterRoot = [System.IO.Path]::GetFullPath((Join-Path $root ".local\postgres17"))
$data = Join-Path $clusterRoot "data"
$credentialsPath = Join-Path $clusterRoot "credentials.json"
$passwordFile = Join-Path $clusterRoot "init-password.txt"

if (-not $clusterRoot.StartsWith($root + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Local cluster must remain inside the project workspace."
}
if (-not $PostgresBin) {
    $PostgresBin = Join-Path $root ".tool-cache\postgresql17\pgsql\bin"
}
$initdb = Join-Path $PostgresBin "initdb.exe"
$psql = Join-Path $PostgresBin "psql.exe"
$createdb = Join-Path $PostgresBin "createdb.exe"
foreach ($binary in @($initdb, $psql, $createdb)) {
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
        throw "PostgreSQL 17 binaries are required at $PostgresBin. See docs/deployment/local.md."
    }
}
$version = & $initdb --version
if ($LASTEXITCODE -ne 0 -or $version -notmatch "PostgreSQL\) 17\.") {
    throw "This script requires PostgreSQL 17 binaries."
}

New-Item -ItemType Directory -Path $clusterRoot -Force | Out-Null
if (Test-Path -LiteralPath $credentialsPath) {
    $credentials = Get-Content -LiteralPath $credentialsPath -Raw | ConvertFrom-Json
    if ($credentials.user -ne "edp_dev" -or $credentials.host -ne "127.0.0.1" -or $credentials.port -ne $Port -or -not $credentials.password) {
        throw "Existing local credentials do not match this cluster configuration."
    }
} else {
    if (Test-Path -LiteralPath (Join-Path $data "PG_VERSION")) {
        throw "Existing cluster has no project credentials file; refusing to change its access."
    }
    $random = [byte[]]::new(32)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($random) } finally { $rng.Dispose() }
    $credentials = [pscustomobject]@{
        user = "edp_dev"
        password = [Convert]::ToBase64String($random).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        host = "127.0.0.1"
        port = $Port
    }
    [System.IO.File]::WriteAllText($credentialsPath, ($credentials | ConvertTo-Json))
}

if (-not (Test-Path -LiteralPath (Join-Path $data "PG_VERSION"))) {
    if ((Test-Path -LiteralPath $data) -and (Get-ChildItem -LiteralPath $data -Force | Select-Object -First 1)) {
        throw "Unrecognized nonempty data directory; refusing to overwrite it."
    }
    [System.IO.File]::WriteAllText($passwordFile, $credentials.password)
    try {
        & $initdb --pgdata $data --username $credentials.user --pwfile $passwordFile --auth scram-sha-256 --encoding UTF8 --locale C
        if ($LASTEXITCODE -ne 0) { throw "Unable to initialize the project PostgreSQL cluster." }
    } finally {
        if (Test-Path -LiteralPath $passwordFile) {
            Remove-Item -LiteralPath $passwordFile
        }
    }
}
if ((Get-Content -LiteralPath (Join-Path $data "PG_VERSION") -Raw).Trim() -ne "17") {
    throw "Existing data directory is not PostgreSQL 17."
}

& (Join-Path $PSScriptRoot "start-local-postgres.ps1") -PostgresBin $PostgresBin -Port $Port
if ($LASTEXITCODE -ne 0) { throw "Unable to start the project PostgreSQL cluster." }
$previousPassword = $env:PGPASSWORD
try {
    $env:PGPASSWORD = $credentials.password
    & $psql --no-password --no-psqlrc --host $credentials.host --port $Port --username $credentials.user --dbname postgres --set ON_ERROR_STOP=on --command "ALTER SYSTEM SET timezone = 'UTC'" --command "ALTER SYSTEM SET log_timezone = 'UTC'" --command "SELECT pg_reload_conf()" *> $null
    if ($LASTEXITCODE -ne 0) { throw "Unable to configure UTC for the project PostgreSQL cluster." }
    foreach ($database in @("edp_dev", "edp_test", "edp_foundation_e2e")) {
        $exists = & $psql --no-password --no-psqlrc --host $credentials.host --port $Port --username $credentials.user --dbname postgres --tuples-only --no-align --command "SELECT 1 FROM pg_database WHERE datname = '$database'"
        if ($LASTEXITCODE -ne 0) { throw "Unable to inspect the project database catalog." }
        if ($exists -ne "1") {
            & $createdb --no-password --host $credentials.host --port $Port --username $credentials.user --owner $credentials.user $database
            if ($LASTEXITCODE -ne 0) { throw "Unable to create synthetic database $database." }
        }
    }
} finally {
    $env:PGPASSWORD = $previousPassword
}
Write-Output "Project PostgreSQL 17 is ready at 127.0.0.1:$Port. Credentials are stored in ignored .local/postgres17/credentials.json."
