from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def quiet_native_logs() -> None:
    """Silence MediaPipe's C++ logging. Must run before mediapipe is imported."""
    os.environ.setdefault("GLOG_minloglevel", "2")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")


def configure_logging(log_file: Path, *, verbose: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=_FORMAT,
        handlers=[file_handler, logging.StreamHandler()],
    )
