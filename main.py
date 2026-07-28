import sys
from PySide6.QtWidgets import QApplication

from ui.eye_widget import FloatingEye


def main():
    """应用程序入口"""
    try:
        app = QApplication(sys.argv)
        eye = FloatingEye()
        eye.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"启动错误: {e}")


if __name__ == "__main__":
    main()
