$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not $IsWindows -and $env:OS -ne "Windows_NT") {
    throw "Build this launcher on Windows to create a Windows EXE."
}

$buildPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $buildPython)) {
    python -m venv (Join-Path $PSScriptRoot ".venv")
}
& $buildPython -m pip install -r launcher\requirements-build.txt
if ($LASTEXITCODE -ne 0) {
    throw "Installing the launcher build tools failed with exit code $LASTEXITCODE."
}
& $buildPython launcher\package_runtime.py
if ($LASTEXITCODE -ne 0) {
    throw "Creating the project bundle failed with exit code $LASTEXITCODE."
}
$bundlePath = Join-Path $repoRoot "build\runtime-bundle.zip"
& $buildPython -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name ResumeOptimizerLauncher `
    --add-data "$bundlePath;." `
    --distpath dist `
    --workpath build\pyinstaller `
    --specpath build `
    launcher\launcher.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Launcher ready: $repoRoot\dist\ResumeOptimizerLauncher.exe"
