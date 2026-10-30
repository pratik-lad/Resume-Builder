"""Build-selected desktop identity; no UI mode selector."""
import os
PROJECT_EDITION = os.environ.get("RESUME_DESKTOP_EDITION") == "projects"
APP_ID = "ResumeOptimizerProjectEdition" if PROJECT_EDITION else "ResumeOptimizerDesktop"
APP_LABEL = "Resume Optimizer Project Edition" if PROJECT_EDITION else "Resume Optimizer Desktop"
GUI_EXE = "ResumeOptimizerProjects.exe" if PROJECT_EDITION else "ResumeOptimizerDesktop.exe"
WORKER_EXE = "ResumeOptimizerProjectsWorker.exe" if PROJECT_EDITION else "ResumeOptimizerWorker.exe"
ENTRYPOINT = "project_main.py" if PROJECT_EDITION else "main.py"
