"""Local installer lifecycle test; never uninstall an existing desktop install."""
from __future__ import annotations

import json
import argparse
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    import winreg
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer")
    parser.add_argument("--project-edition", action="store_true")
    parser.add_argument("--registry-id")
    args = parser.parse_args()
    gui_exe = "ResumeOptimizerProjects.exe" if args.project_edition else "ResumeOptimizerDesktop.exe"
    worker_exe = "ResumeOptimizerProjectsWorker.exe" if args.project_edition else "ResumeOptimizerWorker.exe"
    app_id = "ResumeOptimizerProjectEdition" if args.project_edition else "ResumeOptimizerDesktop"
    args.registry_id = args.registry_id or app_id
    args.installer = args.installer or str(ROOT / ("dist/ResumeOptimizerProjectsSetup.exe" if args.project_edition else "dist/ResumeOptimizerDesktopSetup.exe"))
    if (args.project_edition and args.registry_id != app_id and not args.registry_id.startswith("ResumeOptimizerProjectEditionTest")) or (not args.project_edition and args.registry_id != app_id and not args.registry_id.startswith("ResumeOptimizerDesktopTest")):
        raise ValueError("Use only the application registry ID or an isolated ResumeOptimizerDesktopTest ID.")
    registry_path = "Software\\" + args.registry_id
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            previous = winreg.QueryValueEx(key, "InstallDir")[0]
        raise RuntimeError(f"An existing desktop installation was found at {previous}; lifecycle test skipped to preserve it.")
    except FileNotFoundError:
        pass
    root = Path(tempfile.mkdtemp(prefix="ResumeDesktopInstall-")).resolve()
    target = root / "Application"
    assert target.resolve().is_relative_to(root) and not target.exists()
    data = root / "Data"
    marker_directory = Path(os.environ["LOCALAPPDATA"]) / app_id / ("installer-test-" + uuid.uuid4().hex)
    marker_directory.mkdir(parents=True)
    marker = marker_directory / "preserve.txt"
    marker.write_text("Preserve this user-data marker during upgrade and uninstall.")
    installer = Path(args.installer).resolve()
    flags = subprocess.CREATE_NO_WINDOW
    started = time.perf_counter()
    subprocess.run([str(installer), "/S", "/D=" + str(target)], check=True, timeout=180, creationflags=flags)
    result = {"install_seconds": round(time.perf_counter() - started, 2),
              "clean_windows_vm": False, "test_root": str(root), "registry_id": args.registry_id}
    assert (target / gui_exe).is_file()
    environment = os.environ.copy()
    environment.update(RESUME_DESKTOP_DATA=str(data), QT_QPA_PLATFORM="offscreen",
                       RESUME_DESKTOP_SELF_TEST_MS="500",
                       PATH=os.environ["WINDIR"] + r"\System32;" + os.environ["WINDIR"])
    def launch():
        subprocess.run([str(target / gui_exe)], env=environment, check=True,
                       timeout=30, creationflags=flags, cwd=root)
        record = json.loads((data / "logs/gui-startup.json").read_text())
        assert record["window_created"]
        return record
    result["first_launch"] = launch()
    data.mkdir(exist_ok=True)
    snapshot = {"draft_id": "installer-restore", "resume": "", "document": {
        "sections": [{"key": "summary", "title": "Summary", "text": "Persisted edited draft."}],
        "jd": "Python engineer", "mode": "demo", "requirements": {}, "source": ""}}
    if args.project_edition:
        snapshot["document"].update(edition="projects", schema_version=4)
    (data / "last-draft.json").write_text(json.dumps(snapshot))
    started = time.perf_counter()
    subprocess.run([str(installer), "/S", "/D=" + str(target)], check=True, timeout=180, creationflags=flags)
    result["upgrade_seconds"] = round(time.perf_counter() - started, 2)
    result["restart_after_upgrade"] = launch()
    assert "Persisted edited draft." in (data / "last-draft.json").read_text()
    result["data_preserved_after_upgrade"] = marker.is_file()
    # The child worker resolves every dependency from the installed bundle;
    # PATH deliberately has no Python, Docker or n8n executables.
    worker_env = environment.copy()
    worker_env.pop("RESUME_DESKTOP_SELF_TEST_MS", None)
    completed = subprocess.run([sys.executable, "-u", str(ROOT / "desktop/smoke.py"),
                                "--worker-exe", str(target / worker_exe), "--exports-only"],
                               env=worker_env, check=True, timeout=90, text=True, encoding="utf-8",
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
    result["worker_export_check_passed"] = "export" in completed.stdout
    # Verify the recursive-uninstall target is still the exact isolated install
    # directory, and that its registry entry has not been replaced by another app.
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
        registered = Path(winreg.QueryValueEx(key, "InstallDir")[0]).resolve()
    assert registered == target.resolve() and registered.is_relative_to(root)
    started = time.perf_counter()
    subprocess.run([str(target / "Uninstall.exe"), "/S"], check=True, timeout=60, creationflags=flags)
    deadline = time.monotonic() + 60
    while (target / "_internal").exists() and time.monotonic() < deadline:
        time.sleep(.2)
    assert not (target / "_internal").exists() and not (target / gui_exe).exists()
    result["uninstall_seconds"] = round(time.perf_counter() - started, 2)
    result["data_preserved_after_uninstall"] = marker.is_file() and (data / "last-draft.json").is_file()
    assert result["data_preserved_after_uninstall"]
    (ROOT / "build/desktop-installer-smoke.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
