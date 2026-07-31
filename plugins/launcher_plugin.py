import os
import threading
import urllib.parse
import webbrowser
import sys
from PySide6.QtCore import Qt, QSize, QObject, Signal, QFileInfo, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QWidget, QGroupBox, QCheckBox,
    QFileIconProvider
)
from plugins.base import BasePlugin

# 引入 pypinyin 用于汉字转拼音匹配
try:
    from pypinyin import lazy_pinyin, Style
    PYPINYIN_AVAILABLE = True
except ImportError:
    PYPINYIN_AVAILABLE = False

# 引入 pynput 用于全局快捷键监听
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# Windows 系统级 API 用于强制获取焦点
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # 定义所需的 Windows API 函数
    SetForegroundWindow = user32.SetForegroundWindow
    SetForegroundWindow.argtypes = [wintypes.HWND]
    SetForegroundWindow.restype = wintypes.BOOL

    BringWindowToTop = user32.BringWindowToTop
    BringWindowToTop.argtypes = [wintypes.HWND]
    BringWindowToTop.restype = wintypes.BOOL

    GetForegroundWindow = user32.GetForegroundWindow
    GetForegroundWindow.argtypes = []
    GetForegroundWindow.restype = wintypes.HWND

    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    GetWindowThreadProcessId.restype = wintypes.DWORD

    AttachThreadInput = user32.AttachThreadInput
    AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    AttachThreadInput.restype = wintypes.BOOL

    AllowSetForegroundWindow = user32.AllowSetForegroundWindow
    AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
    AllowSetForegroundWindow.restype = wintypes.BOOL

    # ASFW_ANY 常量
    ASFW_ANY = -1

    # 获取当前进程 ID
    GetCurrentProcessId = kernel32.GetCurrentProcessId
    GetCurrentProcessId.argtypes = []
    GetCurrentProcessId.restype = wintypes.DWORD

    # 用于获取窗口句柄的辅助函数
    def get_window_handle(widget):
        """获取 Qt Widget 的 Windows 窗口句柄"""
        try:
            return int(widget.winId())
        except:
            return None


class HotkeySignalHelper(QObject):
    """跨线程 Qt 信号辅助类：用于将 pynput 子线程的触发事件转发回 Qt UI 主线程"""
    trigger_signal = Signal()


class LauncherDialog(QDialog):
    """模仿 macOS Spotlight 风格的极简搜索框"""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        # 窗口无边框、无系统标题栏、置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.setFixedWidth(640)

        # macOS Spotlight 暗黑风格样式表（优化选中项为柔和浅绿色）
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 35, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px;
            }
            QLineEdit {
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 14px 18px;
                font-size: 18px;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                background-color: transparent;
                color: #e0e0e0;
                border-radius: 8px;
                margin-top: 2px;
                margin-bottom: 2px;
                padding: 8px 14px;
                font-size: 14px;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
            }
            /* 选中与悬停颜色：柔和半透明浅绿背景 + 舒适高亮文本 */
            QListWidget::item:selected, QListWidget::item:hover {
                background-color: rgba(76, 175, 80, 0.35);
                color: #e8f5e9;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.25);
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.init_ui()
        # 初始刷新：无输入时不显示列表
        self.filter_apps("")

        # 安装事件过滤器以捕获焦点事件
        self.search_input.installEventFilter(self)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(6)

        # 搜索输入框
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("🔍 Spotlight 搜索应用或按回车搜索网页...")
        self.search_input.textChanged.connect(self.filter_apps)
        self.search_input.returnPressed.connect(self.launch_selected_app)
        self.layout.addWidget(self.search_input)

        # 搜索结果列表（支持图标展示）
        self.list_widget = QListWidget(self)
        self.list_widget.setIconSize(QSize(24, 24))

        # 支持单击和双击直接启动应用
        self.list_widget.itemClicked.connect(self.launch_selected_app)
        self.list_widget.itemDoubleClicked.connect(self.launch_selected_app)
        self.layout.addWidget(self.list_widget)

        self.list_widget.hide()

    def eventFilter(self, obj, event):
        """事件过滤器：监控输入框的焦点事件"""
        if obj == self.search_input and event.type() == event.Type.FocusOut:
            # 如果输入框失去焦点，延迟重新获取
            QTimer.singleShot(10, self._ensure_focus)
        return super().eventFilter(obj, event)

    def _ensure_focus(self):
        """确保输入框保持焦点"""
        if self.isVisible():
            self.search_input.setFocus(Qt.OtherFocusReason)

    def filter_apps(self, text):
        """根据输入内容过滤列表：支持原名、拼音全拼、首字母搜索"""
        query = text.strip().lower()
        self.list_widget.clear()

        if not query:
            self.list_widget.hide()
            self.adjustSize()
            return

        count = 0
        # cached_apps 格式为: (name, full_path, icon, py_full, py_first)
        for app in self.plugin.cached_apps:
            name, path, icon = app[0], app[1], app[2]
            py_full = app[3] if len(app) > 3 else ""
            py_first = app[4] if len(app) > 4 else ""

            # 匹配逻辑：命中原名 OR 命中全拼 OR 命中拼音首字母
            if (query in name.lower()) or (py_full and query in py_full) or (py_first and query in py_first):
                item = QListWidgetItem(icon, name) if icon else QListWidgetItem(name)
                item.setData(Qt.UserRole, path)
                self.list_widget.addItem(item)
                count += 1
                if count >= 12:  # 最多展示 12 条
                    break

        if self.list_widget.count() > 0:
            self.list_widget.show()
            self.list_widget.setCurrentRow(0)
        else:
            self.list_widget.hide()

        self.adjustSize()

    def launch_selected_app(self):
        """启动选中的应用程序；若无选中应用，则使用系统默认浏览器搜索"""
        current_item = self.list_widget.currentItem()

        # 1. 如果有匹配选中的本地应用，直接启动
        if current_item and self.list_widget.isVisible():
            app_path = current_item.data(Qt.UserRole)
            if app_path and os.path.exists(app_path):
                try:
                    os.startfile(app_path)
                    self.close()
                    return
                except Exception as e:
                    print(f"启动本地应用失败: {e}")

        # 2. 没有匹配应用或未选中时：调用默认浏览器跳转网页搜索
        query_text = self.search_input.text().strip()
        if query_text:
            encoded_query = urllib.parse.quote(query_text)
            search_url = f"https://www.bing.com/search?q={encoded_query}"

            try:
                webbrowser.open(search_url)
            except Exception as e:
                print(f"调起默认浏览器失败: {e}")

        self.close()

    def keyPressEvent(self, event):
        """按 Esc 键取消显示并退出；支持上下键盘按键选择项"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Down and self.list_widget.isVisible():
            curr = self.list_widget.currentRow()
            if curr < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up and self.list_widget.isVisible():
            curr = self.list_widget.currentRow()
            if curr > 0:
                self.list_widget.setCurrentRow(curr - 1)
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """窗口关闭时清空插件持有的窗口句柄引用，避免 C++ 对象删除引起的 RuntimeError"""
        if self.plugin:
            self.plugin.dialog = None
        super().closeEvent(event)

    def showEvent(self, event):
        """窗口显示时自动获取焦点"""
        super().showEvent(event)
        QTimer.singleShot(10, self._ensure_focus)


class LauncherPlugin(BasePlugin):
    """快速启动器插件"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.dialog = None
        self.hotkey_listener = None
        self.cached_apps = []  # 缓存: [(app_name, full_path, QIcon, py_full, py_first), ...]

        self.signal_helper = HotkeySignalHelper()
        self.signal_helper.trigger_signal.connect(self.show_launcher)

        # 初始化时根据 key 读取配置，同步启用/禁用状态与监听器
        setting_key = f"plugin_{self.plugin_id}_enabled"
        is_enabled_setting = self.settings_manager.get_setting(setting_key, "false") == "true"
        if is_enabled_setting:
            self.enable()
        else:
            self.disable()

    @property
    def plugin_id(self) -> str:
        return "quick_launcher"

    @property
    def name(self) -> str:
        return "🚀 快捷应用搜索启动器"

    def enable(self):
        """启用插件：同步父类状态并开启全局快捷键与后台缓存"""
        super().enable()
        self._start_hotkey_listener()
        # 仅在未预加载时开启后台线程预加载应用和图标
        if not self.cached_apps:
            threading.Thread(target=self._preload_apps, daemon=True).start()

    def disable(self):
        """禁用插件：同步父类状态并注销全局快捷键"""
        super().disable()
        self._stop_hotkey_listener()

    def _preload_apps(self):
        """后台预加载应用列表并提取系统图标及拼音索引"""
        paths = [
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        ]

        found_names = set()
        apps_data = []
        icon_provider = QFileIconProvider()

        for base_path in paths:
            if not os.path.exists(base_path):
                continue
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".lnk"):
                        name = os.path.splitext(file)[0]
                        if "uninstall" in name.lower() or name in found_names:
                            continue
                        found_names.add(name)
                        full_path = os.path.join(root, file)

                        try:
                            icon = icon_provider.icon(QFileInfo(full_path))
                        except Exception:
                            icon = QIcon()

                        # 生成拼音全拼与首字母
                        py_full = ""
                        py_first = ""
                        if PYPINYIN_AVAILABLE:
                            # 拼接全拼，例如 ["wei", "xin"] -> "weixin"
                            py_full = "".join(lazy_pinyin(name)).lower()
                            # 拼接首字母，例如 "微信" -> "wx"
                            py_first = "".join(lazy_pinyin(name, style=Style.FIRST_LETTER)).lower()

                        apps_data.append((name, full_path, icon, py_full, py_first))

        self.cached_apps = apps_data

    def _start_hotkey_listener(self):
        if not PYNPUT_AVAILABLE:
            print("[LauncherPlugin] 警告: 未安装 pynput，无法开启全局快捷键监听 (pip install pynput)")
            return

        self._stop_hotkey_listener()

        hotkey_mapping = {
            '<ctrl>+<alt>+<space>': self._on_hotkey_pressed,
            '<ctrl>+<alt>': self._on_hotkey_pressed
        }

        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[LauncherPlugin] 全局热键注册失败: {e}")

    def _stop_hotkey_listener(self):
        if self.hotkey_listener is not None:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
            self.hotkey_listener = None

    def _on_hotkey_pressed(self):
        self.signal_helper.trigger_signal.emit()

    def _force_focus_windows(self, hwnd):
        """Windows 平台强制获取焦点的核心函数"""
        if sys.platform != 'win32' or not hwnd:
            return False

        try:
            AllowSetForegroundWindow(ASFW_ANY)
            foreground_hwnd = GetForegroundWindow()

            if foreground_hwnd != hwnd:
                foreground_thread = GetWindowThreadProcessId(foreground_hwnd, None)
                target_thread = GetWindowThreadProcessId(hwnd, None)

                if foreground_thread != target_thread:
                    AttachThreadInput(target_thread, foreground_thread, True)
                    result = SetForegroundWindow(hwnd)
                    AttachThreadInput(target_thread, foreground_thread, False)
                else:
                    result = SetForegroundWindow(hwnd)

                if result:
                    BringWindowToTop(hwnd)
                    return True

            return False

        except Exception as e:
            print(f"[LauncherPlugin] 强制获取焦点失败: {e}")
            return False

    def show_launcher(self):
        """呼出 Spotlight 风格搜索框"""
        setting_key = f"plugin_{self.plugin_id}_enabled"
        is_setting_enabled = self.settings_manager.get_setting(setting_key, "false") == "true"
        if not self.is_enabled or not is_setting_enabled:
            return

        if self.dialog is not None:
            try:
                if self.dialog.isVisible():
                    self.dialog.activateWindow()
                    self.dialog.raise_()

                    if sys.platform == 'win32':
                        hwnd = get_window_handle(self.dialog)
                        if hwnd:
                            self._force_focus_windows(hwnd)

                    QTimer.singleShot(10, self._focus_search_input)
                    return
                else:
                    self.dialog.deleteLater()
                    self.dialog = None
            except RuntimeError:
                self.dialog = None

        self.dialog = LauncherDialog(self, parent=self.parent())

        screen_geo = self.dialog.screen().geometry()
        x = (screen_geo.width() - self.dialog.width()) // 2
        y = (screen_geo.height()) // 4
        self.dialog.move(x, y)

        self.dialog.show()

        if sys.platform == 'win32':
            hwnd = get_window_handle(self.dialog)
            if hwnd:
                self._force_focus_windows(hwnd)

        QTimer.singleShot(20, self._focus_search_input)

    def _focus_search_input(self):
        """延迟设置焦点的辅助方法，确保搜索框能正确获取焦点"""
        if not self.dialog:
            return
        try:
            if not self.dialog.isVisible():
                return

            self.dialog.activateWindow()
            self.dialog.raise_()

            self.dialog.search_input.setFocus(Qt.OtherFocusReason)
            self.dialog.search_input.selectAll()

            if not self.dialog.search_input.hasFocus() and sys.platform == 'win32':
                hwnd = get_window_handle(self.dialog.search_input)
                if hwnd:
                    user32.SetFocus(hwnd)

        except RuntimeError:
            self.dialog = None

    def create_settings_widget(self, parent=None) -> QWidget:
        group = QGroupBox("🚀 快捷应用启动器", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        chk_enable = QCheckBox("启用 CTRL+ALT 快捷唤起搜索框", group)

        setting_key = f"plugin_{self.plugin_id}_enabled"
        is_enabled = self.settings_manager.get_setting(setting_key, "false") == "true"
        chk_enable.setChecked(is_enabled)

        def on_toggle(checked):
            self.settings_manager.set_setting(setting_key, "true" if checked else "false")
            if checked:
                self.enable()
            else:
                self.disable()

        chk_enable.toggled.connect(on_toggle)
        layout.addWidget(chk_enable)
        return group