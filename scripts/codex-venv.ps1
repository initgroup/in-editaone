$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
chcp.com 65001 | Out-Null

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "venv Python not found: $venvPython"
}

Push-Location -LiteralPath $repoRoot
$previousErrorActionPreference = $ErrorActionPreference
try {
    # Native stderr is a normal output stream; the exit code determines failure.
    $ErrorActionPreference = 'Continue'
    & $venvPython @args
    $pythonExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Pop-Location
}
exit $pythonExitCode
