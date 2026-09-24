from __future__ import annotations

"""Application-wide logging.

Artmach Compass is launched as a windowed .exe (via Install_Prototype.cmd ->
explorer.exe), so there is no console attached: anything printed to
stdout/stderr, and every Qt-level warning/critical message (which is how
Qt3D reports missing plugins, failed scene imports, etc.), was previously
invisible. This module routes all of that into a single log file on disk
plus captures uncaught Python exceptions, so a real diagnostic trail exists
even when the app is double-clicked with no terminal in sight.
"""

import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

_LOGGER_NAME = "artmach_compass"
_logger: logging.Logger | None = None


def logs_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    base = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
    root = base / "ArtmachCompass" / "logs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def log_file_path() -> Path:
    return logs_root() / "compass.log"


def _qt_message_handler(msg_type: QtMsgType, context, message: str) -> None:
    logger = get_logger()
    origin = ""
    if getattr(context, "file", None):
        origin = f" ({context.file}:{context.line})"
    if msg_type == QtMsgType.QtDebugMsg:
        logger.debug("Qt: %s%s", message, origin)
    elif msg_type == QtMsgType.QtInfoMsg:
        logger.info("Qt: %s%s", message, origin)
    elif msg_type == QtMsgType.QtWarningMsg:
        logger.warning("Qt: %s%s", message, origin)
    elif msg_type == QtMsgType.QtCriticalMsg:
        logger.error("Qt: %s%s", message, origin)
    elif msg_type == QtMsgType.QtFatalMsg:
        logger.critical("Qt FATAL: %s%s", message, origin)


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    get_logger().critical(
        "Unhandled exception:\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
    )
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def setup_logging() -> Path:
    """Install the rotating file log, Qt message capture, and crash hook.

    Safe to call more than once - later calls are no-ops. Returns the path
    to the active log file so callers (e.g. the UI) can show/open it.
    """
    global _logger
    path = log_file_path()
    if _logger is not None:
        return path

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    _logger = logger

    qInstallMessageHandler(_qt_message_handler)
    sys.excepthook = _excepthook

    logger.info("=== Artmach Compass session started (log: %s) ===", path)
    return path


def get_logger() -> logging.Logger:
    if _logger is None:
        setup_logging()
    return _logger


def log_action(message: str, *args: object) -> None:
    """Record a user/application action (button click, selection, stage, ...)."""
    get_logger().info(message, *args)


def log_error(message: str, *args: object) -> None:
    get_logger().error(message, *args)
