import ctypes
from PySide6.QtCore import QThread, Signal
from capture.screenshot import ScreenshotManager, QT_MULTIMEDIA_AVAILABLE


class MonitorThread(QThread):
    """窗口监控线程 - 后台监控活动窗口变化"""

    activity_changed = Signal(str, str)

    def __init__(self, settings_manager=None):
        super().__init__()
        self.switch_count = 0
        self.last_title = ""
        self.running = True
        self.seen_titles = set()
        self.total_switches = 0
        self.settings_manager = settings_manager
        self.load_settings()

        # 初始化相机检查
        if QT_MULTIMEDIA_AVAILABLE:
            ScreenshotManager.check_camera_available()
        else:
            print("ℹ️ 相机功能不可用，将使用截图模式")

    def load_settings(self):
        """加载设置"""
        if self.settings_manager:
            self.use_camera = self.settings_manager.get_setting('use_camera', 'true') == 'true'
            self.use_screenshot = self.settings_manager.get_setting('use_screenshot', 'true') == 'true'
            self.capture_interval = int(self.settings_manager.get_setting('capture_interval', '3'))
        else:
            self.use_camera = True
            self.use_screenshot = True
            self.capture_interval = 3

        print(f"📋 设置: 相机={self.use_camera}, 截图={self.use_screenshot}, 间隔={self.capture_interval}")

    def update_settings(self):
        """更新设置（在运行时）"""
        self.load_settings()

    def run(self):
        """线程主循环"""
        user32 = ctypes.windll.user32

        while self.running:
            self.sleep(3)

            try:
                hwnd = user32.GetForegroundWindow()
                if hwnd:
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value

                        if title and title != "Unknown" and title != "":
                            if title != self.last_title:
                                self.last_title = title
                                self.total_switches += 1
                                print(f"🔄 窗口切换: {title} (第 {self.total_switches} 次切换)")

                                screenshot_base64 = None

                                # 按间隔触发媒体捕获
                                if self.total_switches % self.capture_interval == 0:
                                    print(f"📷 触发媒体捕获 (第 {self.total_switches} 次切换)")
                                    screenshot_base64 = ScreenshotManager.capture_media(
                                        use_camera=self.use_camera,
                                        use_screenshot=self.use_screenshot
                                    )

                                    if screenshot_base64:
                                        print(f"📷 已捕获媒体 (第 {self.total_switches} 次切换)")
                                    else:
                                        print(f"⚠️ 媒体捕获失败 (第 {self.total_switches} 次切换)")

                                    self.total_switches = 0

                                self.activity_changed.emit(title, screenshot_base64)
            except Exception as e:
                print(f"监控线程错误: {e}")

    def stop(self):
        """停止线程"""
        self.running = False
