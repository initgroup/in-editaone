param(
    [string]$Url = 'http://127.0.0.1:8000/',
    [string]$DestinationDirectory
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$iconPath = Join-Path $projectRoot 'frontend\favicon.ico'
if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
    throw "Icon not found: $iconPath"
}
$targetUri = $null
if (-not [Uri]::TryCreate($Url, [UriKind]::Absolute, [ref]$targetUri) -or $targetUri.Scheme -notin @('http', 'https')) {
    throw 'Url must be an absolute HTTP or HTTPS address.'
}
if ([string]::IsNullOrWhiteSpace($DestinationDirectory)) {
    $DestinationDirectory = [Environment]::GetFolderPath('DesktopDirectory')
}
if (-not (Test-Path -LiteralPath $DestinationDirectory -PathType Container)) {
    throw "Destination directory not found: $DestinationDirectory"
}
# Use code points so Windows PowerShell 5.1 can load this UTF-8 script without a BOM.
$productName = -join (0xC778, 0xC5D0, 0xB514, 0xD0C0, 0xC6D0 | ForEach-Object { [char]$_ })
$shortcutPath = Join-Path $DestinationDirectory "$productName.url"
$content = "[InternetShortcut]`r`nURL=$($targetUri.AbsoluteUri)`r`nIconFile=$iconPath`r`nIconIndex=0`r`n"
[System.IO.File]::WriteAllText($shortcutPath, $content, [System.Text.Encoding]::Unicode)
Write-Output "Created: $shortcutPath"
Write-Output "URL: $($targetUri.AbsoluteUri)"
Write-Output "Icon: $iconPath"
