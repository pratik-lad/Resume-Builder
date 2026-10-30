"""Independent Project Edition executable entrypoint."""
import os
import sys
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["RESUME_DESKTOP_EDITION"] = "projects"
from desktop.main import main
if __name__ == "__main__":
    main()
