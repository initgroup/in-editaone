param([switch]$CheckOnly)
. (Join-Path $PSScriptRoot 'service-common.ps1')
$state = Get-ManagedService
if (-not $state) { Write-Host 'No managed IN-EDITAONE service is running.'; return }
if ($CheckOnly) { Write-Host "Managed IN-EDITAONE PID: $($state.ProcessId)"; return }
# Only the process whose executable, command line and creation time were verified is stopped.
& taskkill.exe /PID $state.ProcessId /T /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Unable to stop the verified service process tree.' }
Wait-Process -Id $state.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $serviceStatePath -Force
Write-Host 'IN-EDITAONE stopped.'
