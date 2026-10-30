param([string]$NSISCompiler = "")
$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Create desktop/.venv and install desktop/requirements.txt first." }
function Invoke-CheckedNative {
    param([string]$Executable, [string[]]$Arguments, [string]$Failure)
    # Windows PowerShell can turn redirected native stderr (including ordinary
    # Python warnings and PyInstaller progress) into a terminating error record.
    # Keep diagnostics visible and decide success using the native exit code.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Executable @Arguments 2>&1 | ForEach-Object { $_.ToString() }
        $nativeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($nativeExitCode -ne 0) { throw "$Failure (exit $nativeExitCode)" }
}
Invoke-CheckedNative -Executable $python -Arguments @("desktop/prepare_assets.py") -Failure "Asset preparation failed."
Invoke-CheckedNative -Executable $python -Arguments @("-m", "pytest", "desktop/test_generation.py", "desktop/test_desktop.py", "desktop/test_project_edition.py", "desktop/test_project_quality.py", "desktop/test_project_profile.py", "desktop/test_general_quality.py", "desktop/test_reference_release.py", "desktop/test_evidence_quality.py", "desktop/test_skill_coverage.py", "-q") -Failure "Regression checks failed."
$dist = Join-Path $projectRoot ("dist\projects-" + [guid]::NewGuid().ToString("N"))
Invoke-CheckedNative -Executable $python -Arguments @("-m", "PyInstaller", "--noconfirm", "--distpath", $dist, "--workpath", "build/project-pyinstaller", "desktop/project.spec") -Failure "Project Edition packaging failed."
if (-not $NSISCompiler) { $NSISCompiler = (Get-Command makensis -ErrorAction Stop).Source }
$stage = Join-Path $env:TEMP ("ResumeProjects-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $stage | Out-Null
$bundle = Join-Path $stage "bundle"
New-Item -ItemType Junction -Path $bundle -Target (Join-Path $dist "ResumeOptimizerProjects") | Out-Null
$stagedInstaller = Join-Path $stage "ResumeOptimizerProjectsSetup.exe"
$assetSpec = Get-Content -LiteralPath (Join-Path $PSScriptRoot "assets.json") -Raw | ConvertFrom-Json
$installerArguments = @("/DBUNDLE_DIR=$bundle", "/DSETUP_OUT=$stagedInstaller", "/DMODEL_FILENAME=$($assetSpec.model.filename)")
if ($assetSpec.model.size -gt 1700000000) { $installerArguments += "/DLARGE_MODEL" }
$installerArguments += "desktop/project_installer.nsi"
Invoke-CheckedNative -Executable $NSISCompiler -Arguments $installerArguments -Failure "Project Edition installer failed. For 2-4 GB models use the documented NSISBI compiler."
$installer = Join-Path $projectRoot "dist/ResumeOptimizerProjectsSetup.exe"
if (Test-Path -LiteralPath $installer) {
    $backup = Join-Path $projectRoot ("dist/ResumeOptimizerProjectsSetup-backup-" + [guid]::NewGuid().ToString("N") + ".exe")
    Copy-Item -LiteralPath $installer -Destination $backup
}
Copy-Item -LiteralPath $stagedInstaller -Destination $installer
$installerHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$versionText = Get-Content -LiteralPath (Join-Path $PSScriptRoot "project_installer.nsi") -Raw
$releaseVersion = [regex]::Match($versionText, 'DISPLAY_VERSION "([^"]+)"').Groups[1].Value
$manifest = @{version=$releaseVersion; app_id="ResumeOptimizerProjectEdition"; bundle=(Join-Path $dist "ResumeOptimizerProjects"); installer=$installer; sha256=$installerHash; installer_size_bytes=(Get-Item -LiteralPath $installer).Length; model=$assetSpec.model}
$manifest | ConvertTo-Json | Set-Content build/project-latest.json -Encoding UTF8
$manifest | ConvertTo-Json | Set-Content dist/ResumeOptimizerProjects-manifest.json -Encoding UTF8
"$installerHash  ResumeOptimizerProjectsSetup.exe" | Set-Content dist/ResumeOptimizerProjectsSetup.exe.sha256 -Encoding ASCII
