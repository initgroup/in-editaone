param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'service-common.ps1')
$source = $repoRoot
$destination = Join-Path (Split-Path -Parent $source) 'in-editaone'
if ((Split-Path -Leaf $source) -eq 'in-editaone') {
    Write-Host "Already renamed: $source"
    return
}
Set-Location (Split-Path -Parent $source)
if ($CheckOnly) {
    & (Join-Path $PSScriptRoot 'rename-project.ps1') -CheckOnly
    return
}
# Preserve the existing managed service settings across the directory move.
$service = Get-ManagedService
$startOptions = @{}
if ($service) {
    $startOptions.Port = [int]$service.Port
    $startOptions.BindAddress = [string]$service.BindAddress
    $identity = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$service.ProcessId)"
    $startOptions.Reload = $identity.CommandLine -match '(?:^|\s)--reload(?:\s|$)'
}
& (Join-Path $PSScriptRoot 'stop-service.ps1')
try {
    & (Join-Path $PSScriptRoot 'rename-project.ps1')
} catch {
    if ($service -and (Test-Path -LiteralPath (Join-Path $source 'scripts\start-service.ps1'))) {
        & (Join-Path $source 'scripts\start-service.ps1') @startOptions
    }
    throw
}
if ($service) { & (Join-Path $destination 'scripts\start-service.ps1') @startOptions }
& (Join-Path $destination 'venv\Scripts\pip.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'pip launcher verification failed.' }
& (Join-Path $destination 'venv\Scripts\uvicorn.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'uvicorn launcher verification failed.' }
Write-Host "Open this project in VS Code: $destination"
