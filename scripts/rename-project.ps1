param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$parent = Split-Path -Parent $source
$destination = [IO.Path]::GetFullPath((Join-Path $parent 'in-editaone'))
if ((Split-Path -Leaf $source) -eq 'in-editaone') { Write-Host "Already renamed: $source"; return }
if ((Split-Path -Leaf $source) -ne 'data-editing-system' -or
    (Split-Path -Parent $destination) -ne $parent -or
    -not (Test-Path -LiteralPath (Join-Path $source 'main.py')) -or
    -not (Test-Path -LiteralPath (Join-Path $source '.git'))) {
    throw 'Unexpected source or destination. Nothing was moved.'
}
if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination" }
if ($CheckOnly) { Write-Host "$source -> $destination"; return }
$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -like "*$source*"
}
if ($running) { throw 'Stop this project Python services and terminals before renaming.' }
Set-Location $parent
try { Rename-Item -LiteralPath $source -NewName 'in-editaone' -ErrorAction Stop }
catch { throw ('Unable to rename the directory: ' + $_.Exception.Message + ' Close this project in VS Code/Codex and retry from an external PowerShell window.') }
$python = Join-Path $destination 'venv\Scripts\python.exe'
if (Test-Path -LiteralPath $python) {
    & $python (Join-Path $destination 'scripts\repair-venv-paths.py')
    if ($LASTEXITCODE -ne 0) { throw "Directory renamed to $destination, but venv launcher repair failed." }
}
Write-Host "Project renamed: $destination"
