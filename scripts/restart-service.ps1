param([ValidateRange(1, 65535)][int]$Port = 8000, [string]$BindAddress = '127.0.0.1', [switch]$CheckOnly, [switch]$Reload)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'stop-service.ps1') -CheckOnly:$CheckOnly
& (Join-Path $PSScriptRoot 'start-service.ps1') -Port $Port -BindAddress $BindAddress -CheckOnly:$CheckOnly -Reload:$Reload
