param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [string]$BindAddress = '127.0.0.1',
    [switch]$CheckOnly,
    [switch]$Reload
)
. (Join-Path $PSScriptRoot 'service-common.ps1')
if (-not (Test-Path -LiteralPath $venvPython)) { throw 'Create venv and install requirements.txt first.' }
if (Get-ManagedService) { Write-Host 'IN-EDITAONE is already running.'; return }
if ($CheckOnly) { Write-Host "IN-EDITAONE root: $repoRoot"; Write-Host "Python: $venvPython"; return }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
    throw "Port $Port is already occupied. The existing process was not changed."
}
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$arguments = @('-m', 'uvicorn', 'main:app', '--app-dir', ('"{0}"' -f $repoRoot), '--host', $BindAddress, '--port', $Port)
if ($Reload) { $arguments += '--reload' }
$process = Start-Process -FilePath $venvPython -ArgumentList $arguments -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $runtimeDir 'service.out.log') -RedirectStandardError (Join-Path $runtimeDir 'service.err.log')
$identity = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)"
if (-not $identity) { throw 'Service exited during startup. Inspect .runtime/service.err.log locally.' }
$state = @{ ProcessId = $process.Id; Created = $identity.CreationDate.ToUniversalTime().ToString('o'); Port = $Port; BindAddress = $BindAddress }
$state | ConvertTo-Json | Set-Content -LiteralPath $serviceStatePath -Encoding UTF8
$checkHost = if ($BindAddress -eq '0.0.0.0') { '127.0.0.1' } else { $BindAddress }
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $process.Refresh()
    if ($process.HasExited) { throw 'Service exited. Inspect .runtime/service.err.log locally.' }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://${checkHost}:$Port/api/health" -TimeoutSec 1
        if ($response.StatusCode -eq 200) { Write-Host "IN-EDITAONE started: http://${checkHost}:$Port"; return }
    } catch { }
    Start-Sleep -Milliseconds 500
}
throw 'Service started but health did not become ready. Inspect .runtime/service.err.log locally.'
