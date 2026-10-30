param([string]$NSISCompiler = "")
$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot
if ($env:OS -ne "Windows_NT") { throw "Build on Windows 11 x64." }
$desktopPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $desktopPython)) {
    python -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
& $desktopPython -m pip install -r desktop\requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Desktop dependency installation failed." }
& $desktopPython desktop\prepare_assets.py
if ($LASTEXITCODE -ne 0) { throw "Offline asset verification failed." }
& $desktopPython -m pytest desktop\test_desktop.py desktop\test_generation.py -q
if ($LASTEXITCODE -ne 0) { throw "Desktop regression checks failed." }
$desktopDist = Join-Path $projectRoot ("dist\desktop-" + [guid]::NewGuid().ToString("N"))
& $desktopPython -m PyInstaller --noconfirm --distpath $desktopDist --workpath build\desktop-pyinstaller desktop\desktop.spec
if ($LASTEXITCODE -ne 0) { throw "Desktop freezing failed." }
$nsisCommand = Get-Command makensis -ErrorAction SilentlyContinue
if ($NSISCompiler) {
    $nsisPath = (Resolve-Path $NSISCompiler).Path
} elseif (-not $nsisCommand) {
    $nsisPath = Join-Path ${env:ProgramFiles(x86)} "NSIS\makensis.exe"
    if (-not (Test-Path $nsisPath)) { throw "Install NSIS 3, then rerun build.ps1. The portable app is already in dist\ResumeOptimizerDesktop." }
} else { $nsisPath = $nsisCommand.Source }
Push-Location desktop
try {
    # A short directory junction avoids Win32 MAX_PATH failures when the
    # checkout lives in a deeply nested folder, without duplicating the model.
    $desktopStage = Join-Path $env:TEMP ("ResumeDesktopBuild-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $desktopStage | Out-Null
    $desktopBundle = Join-Path $desktopStage "bundle"
    New-Item -ItemType Junction -Path $desktopBundle -Target (Join-Path $desktopDist "ResumeOptimizerDesktop") | Out-Null
    $assetSpec = Get-Content -LiteralPath (Join-Path $PSScriptRoot "assets.json") -Raw | ConvertFrom-Json
    $installerArguments = @("/DBUNDLE_DIR=$desktopBundle", "/DMODEL_FILENAME=$($assetSpec.model.filename)")
    if ($assetSpec.model.size -gt 1700000000) { $installerArguments += "/DLARGE_MODEL" }
    $installerArguments += "installer.nsi"
    & $nsisPath @installerArguments
    if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }
} finally { Pop-Location }
Write-Host "Offline installer: $projectRoot\dist\ResumeOptimizerDesktopSetup.exe"
Write-Host "Portable application: $desktopDist\ResumeOptimizerDesktop\ResumeOptimizerDesktop.exe"
@{bundle = (Join-Path $desktopDist "ResumeOptimizerDesktop"); installer = (Join-Path $projectRoot "dist\ResumeOptimizerDesktopSetup.exe")} | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $projectRoot "build\desktop-latest.json")
