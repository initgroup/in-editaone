param(
    [ValidateSet("Git", "Working")]
    [string]$Mode = "Git",

    [string]$BackupRoot = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($BackupRoot)) {
    $BackupRoot = Join-Path (Split-Path -Parent $repoRoot) "backup"
}

$BackupRoot = [IO.Path]::GetFullPath($BackupRoot)
if ($BackupRoot.TrimEnd('\') -eq $repoRoot.TrimEnd('\') -or
    $BackupRoot.StartsWith($repoRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'BackupRoot must be outside the project to prevent recursive backups.'
}
$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$backupDir = Join-Path $BackupRoot "in-editaone-$($Mode.ToLower())-$stamp"

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

if ($Mode -eq "Git") {
    $zipPath = Join-Path $env:TEMP "in-editaone-$stamp.zip"
    if (Test-Path $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    Push-Location $repoRoot
    try {
        git archive --format=zip --output="$zipPath" HEAD
        if ($LASTEXITCODE -ne 0) { throw 'git archive failed.' }
        Expand-Archive -LiteralPath $zipPath -DestinationPath $backupDir -Force
    }
    finally {
        Pop-Location
        if (Test-Path $zipPath) {
            Remove-Item -LiteralPath $zipPath -Force
        }
    }
}
else {
    $excludeDirs = @(
        ".git",
        ".aws",
        ".codex",
        "venv",
        ".venv",
        "node_modules",
        ".node_modules",
        "secreats",
        ".secreats",
        "secrets",
        (Join-Path $repoRoot "etc\secrets"),
        "instantclient",
        ".instantclient",
        ".runtime",
        "tmp",
        "playwright-report",
        "test-results",
        ".pytest_cache",
        "__pycache__"
    )
    $excludeFiles = @(
        ".env",
        ".env.*",
        "*Wallet*.zip",
        "*.pem",
        "*.key",
        "*.log",
        "*.pyc"
    )

    $args = @(
        $repoRoot,
        $backupDir,
        "/E",
        "/NFL",
        "/NDL",
        "/R:2",
        "/W:1",
        "/XD"
    ) + $excludeDirs + @("/XF") + $excludeFiles

    robocopy @args
    $exitCode = $LASTEXITCODE
    if ($exitCode -gt 7) {
        throw "robocopy failed with exit code $exitCode"
    }
    $envTemplate = Join-Path $repoRoot '.env.example'
    if (Test-Path -LiteralPath $envTemplate) {
        Copy-Item -LiteralPath $envTemplate -Destination (Join-Path $backupDir '.env.example')
    }
}

Write-Host ""
Write-Host "Backup completed." -ForegroundColor Green
Write-Host "Mode: $Mode"
Write-Host "Path: $backupDir"
