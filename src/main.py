import sys
import traceback
from pathlib import Path

if __name__ == "__main__":
    try:
        from pdf_toolbox.startup import launch

        raise SystemExit(launch())
    except Exception:
        if "--smoke-test" in sys.argv:
            Path(sys.argv[0]).resolve().with_name("pdf-toolbox-smoke-error.txt").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
            raise SystemExit(1) from None
        raise
