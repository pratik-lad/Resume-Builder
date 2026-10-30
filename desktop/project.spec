from pathlib import Path
import os
os.environ["RESUME_BUILD_PROJECT_EDITION"] = "1"
exec(compile((Path(SPECPATH) / "desktop.spec").read_text(encoding="utf-8"), "desktop.spec", "exec"))
