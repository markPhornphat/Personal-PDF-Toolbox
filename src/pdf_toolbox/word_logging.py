"""Small rotating diagnostic log without document content or images."""

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from tempfile import gettempdir
from threading import Lock

_lock = Lock()


def word_logger():
    logger = logging.getLogger("pdf_toolbox.word")
    with _lock:
        if not logger.handlers:
            try:
                folder = Path(os.environ.get("LOCALAPPDATA", gettempdir())) / "PDF Toolbox" / "logs"
                folder.mkdir(parents=True, exist_ok=True)
                handler = RotatingFileHandler(
                    folder / "word.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
                )
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                logger.addHandler(handler)
            except OSError:
                logger.addHandler(logging.NullHandler())
            logger.setLevel(logging.INFO)
            logger.propagate = False
    return logger


def record_error(stage, error):
    word_logger().error(
        "stage=%s exception=%s hresult=%s winerror=%s",
        stage,
        type(error).__name__,
        getattr(error, "hresult", None),
        getattr(error, "winerror", None),
    )
