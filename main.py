import sys
import os
import logging
from PySide6.QtWidgets import QApplication

from ui.eye_widget import FloatingEye


def _setup_logging():
    try:
        log_path = os.path.join(os.path.expanduser("~"), "floating-eye.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        logging.info("FloatingEye starting up")
    except Exception:
        # If logging setup fails, fall back to console logging
        logging.basicConfig(level=logging.INFO)


def _excepthook(exc_type, exc_value, exc_tb):
    # Ensure uncaught exceptions are recorded to the log for later diagnosis
    logging.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))
    # Call the default excepthook (prints to stderr)
    sys.__excepthook__(exc_type, exc_value, exc_tb)
    # Exit with a non-zero status to indicate failure
    sys.exit(1)


def main():
    """应用程序入口"""
    _setup_logging()
    sys.excepthook = _excepthook

    try:
        app = QApplication(sys.argv)
        eye = FloatingEye()
        eye.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception("启动错误: %s", e)
        # make sure we exit with non-zero code on fatal startup error
        sys.exit(1)


if __name__ == "__main__":
    main()
