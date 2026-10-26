$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimeDir = Join-Path $repoRoot '.runtime'
$serviceStatePath = Join-Path $runtimeDir 'service.json'
$venvPython = Join-Path $repoRoot 'venv\Scripts\python.exe'

function Get-ManagedService {
    if (-not (Test-Path -LiteralPath $serviceStatePath)) { return $null }
    $state = Get-Content -LiteralPath $serviceStatePath -Raw | ConvertFrom-Json
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$state.ProcessId)"
    if (-not $process) { return $null }
    $created = $process.CreationDate.ToUniversalTime().ToString('o')
    if ($created -ne $state.Created -or $process.ExecutablePath -ne $venvPython -or
        $process.CommandLine -notlike '*-m uvicorn main:app*' -or
        $process.CommandLine -notlike "*--app-dir*${repoRoot}*") {
        throw 'Service identity does not match this project. No process was stopped.'
    }
    return $state
}
