import sys
import os
import logging
from PySide6.QtWidgets import QApplication

from ui.eye_widget import FloatingEye
from core.database import DatabaseManager

db_manager = DatabaseManager()


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
    # 1. 记录崩溃日志到数据库 (新增)
    try:
        db_manager.add_crash_log(exc_type, exc_value, exc_tb)
    except Exception as e:
        print(f"写入闪退日志失败: {e}")

    # 2. 保留原有的本地文件日志
    logging.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    # 3. 调用默认的 excepthook 并在终端打印
    sys.__excepthook__(exc_type, exc_value, exc_tb)
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
        # 启动过程中如果抛出异常，也保存日志
        db_manager.add_crash_log(type(e), e, e.__traceback__)
        logging.exception("启动错误: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()