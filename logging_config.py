"""Logging setup for PawPal+.

Configures a single logger that writes to both the console and
``logs/pawpal.log``. The agent logs every Plan/Act/Check step here so the
system's behavior is auditable. API keys are never passed to the logger.
"""

from __future__ import annotations

import logging
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "pawpal.log"

_configured = False


def get_logger(name: str = "pawpal") -> logging.Logger:
    """Return the shared PawPal+ logger, configuring handlers once."""
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        LOG_DIR.mkdir(exist_ok=True)
        logger.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(fmt)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)

        # Avoid duplicate handlers if this module is imported repeatedly.
        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        logger.propagate = False

        _configured = True

    return logger
