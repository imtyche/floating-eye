import sys
import os
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from ui.eye_widget import FloatingEye
from core.database import DatabaseManager

db_manager = DatabaseManager()

# 定义一个唯一的本地服务名称（尽量唯一）
SINGLE_INSTANCE_SERVER_NAME = "FloatingEye_Unique_Single_Instance_Lock"


def _setup_logging():
    try:
        # 如果是打包后的环境，取 exe 所在目录；否则取当前 py 文件所在目录
        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))

        log_path = os.path.join(current_dir, "floating-eye.log")

        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            encoding='utf-8'
        )
        logging.info("FloatingEye starting up")
    except Exception:
        logging.basicConfig(level=logging.INFO)


def _excepthook(exc_type, exc_value, exc_tb):
    # 1. 记录崩溃日志到数据库
    try:
        db_manager.add_crash_log(exc_type, exc_value, exc_tb)
    except Exception as e:
        print(f"写入闪退日志失败: {e}")

    # 2. 保留原有的本地文件日志
    logging.exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    # 3. 调用默认的 excepthook 并在终端打印
    sys.__excepthook__(exc_type, exc_value, exc_tb)
    sys.exit(1)


def is_already_running(server_name: str) -> bool:
    """检查是否有已有实例在运行"""
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    # 尝试连接，等待 500ms
    if socket.waitForConnected(500):
        socket.disconnectFromServer()
        return True
    return False


def main():
    """应用程序入口"""
    _setup_logging()
    sys.excepthook = _excepthook

    # 初始化 QApplication（弹出 QMessageBox 依赖 QApplication 的初始化）
    app = QApplication(sys.argv)

    # ------------------ 单例检测逻辑 ------------------
    if is_already_running(SINGLE_INSTANCE_SERVER_NAME):
        QMessageBox.warning(
            None,
            "程序重复启动",
            "FloatingEye 已经在运行中，请勿重复启动！",
            QMessageBox.StandardButton.Ok
        )
        sys.exit(0)

    # 创建本地 Server，保证后续再次启动时能被捕捉到
    local_server = QLocalServer()
    # 防范上一次非正常退出残留的服务文件
    QLocalServer.removeServer(SINGLE_INSTANCE_SERVER_NAME)
    if not local_server.listen(SINGLE_INSTANCE_SERVER_NAME):
        logging.error("无法启动单例服务监听: %s", local_server.errorString())
    # --------------------------------------------------

    try:
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