from __future__ import annotations

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from desktop.bootstrap import initialize
    initialize()
    if "--worker" in sys.argv:
        from desktop.worker import run
        run()
    else:
        import logging
        from desktop.bootstrap import DATA
        logging.basicConfig(filename=DATA / "logs/desktop.log", level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        def exception_hook(kind, error, trace):
            logging.error("Desktop failure", exc_info=(kind, error, trace))
        sys.excepthook = exception_hook
        from desktop.app import run
        run()


if __name__ == "__main__":
    import os
    os.environ["RESUME_DESKTOP_EDITION"] = "legacy"
    main()
