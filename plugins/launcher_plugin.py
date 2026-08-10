import os
import math
import random
import threading
import urllib.parse
import webbrowser
import sys

from PySide6.QtCore import Qt, QSize, QObject, Signal, QFileInfo, QTimer, QPointF
from PySide6.QtGui import QIcon, QPainter, QColor, QBrush, QPen, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QWidget, QGroupBox, QCheckBox, QFileIconProvider
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
    ASFW_ANY = -1

    GetCurrentProcessId = kernel32.GetCurrentProcessId
    GetCurrentProcessId.argtypes = []
    GetCurrentProcessId.restype = wintypes.DWORD

    def get_window_handle(widget):
        """获取 Qt Widget 的 Windows 窗口句柄"""
        try:
            return int(widget.winId())
        except:
            return None

class Particle:
    """单个粒子的物理属性定义"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        # 限制只向右下方扩散 (角度 0 到 90 度，即 0 到 pi/2)
        angle = random.uniform(0.1, math.pi / 2 - 0.1)
        speed = random.uniform(1.2, 3.2) # 调低速度，更轻柔
        self.vx = speed * math.cos(angle) # 向右的平移速度
        self.vy = speed * math.sin(angle) # 向下的平移速度
        # 精致微小粒子 (直径 1.5 到 3.5 像素)
        self.size = random.uniform(1.5, 3.5)
        self.alpha = 255.0
        self.fade_rate = random.uniform(12.0, 20.0) # 透明度衰减速度

        # 柔和细腻的配色
        colors = [
            QColor(76, 175, 80),   # 薄荷绿
            QColor(255, 255, 255), # 柔白
            QColor(180, 225, 182), # 浅绿
            QColor(255, 224, 130)  # 暖金
        ]
        self.color = random.choice(colors)

    def update(self):
        """更新粒子位置与透明度"""
        self.x += self.vx
        self.y += self.vy
        self.alpha -= self.fade_rate
        return self.alpha > 0

class ParticleOverlay(QWidget):
    """覆盖在窗口顶层的粒子特效画布，穿透鼠标事件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 允许鼠标穿透粒子画板
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.particles = []
        # 定时器刷新动画 (60 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(16)

    def add_burst(self, pos: QPointF, count=8):
        """在指定点触发向右下方的微型粒子炸裂（默认 8 个粒子的轻量组合）"""
        for _ in range(count):
            self.particles.append(Particle(pos.x(), pos.y()))

    def update_particles(self):
        """逻辑更新与重绘"""
        if not self.particles:
            return
        # 保留未死亡的粒子
        self.particles = [p for p in self.particles if p.update()]
        self.update() # 触发 paintEvent

    def paintEvent(self, event):
        """渲染所有活动粒子"""
        if not self.particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for p in self.particles:
            c = QColor(p.color)
            c.setAlpha(max(0, int(p.alpha)))
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(p.x, p.y), p.size / 2, p.size / 2)

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
        self.setFixedWidth(680) # macOS Spotlight 宽度约为 680-700px

        # ==========================================
        # macOS 风格深度定制样式表
        # ==========================================
        self.setStyleSheet("""
            /* 1. 主窗口背景：深邃、半透明、大圆角 */
            QDialog {
                background-color: rgba(30, 30, 35, 0.92); /* 更深邃的灰底，提升对比度 */
                border: 1px solid rgba(255, 255, 255, 0.12); /* 微妙的高光边框 */
                border-radius: 14px; /* 更加圆润的圆角 */
            }
            
            /* 2. 搜索输入框：大字号、无边框、极简风格 */
            QLineEdit {
                background-color: transparent;
                color: #FFFFFF;
                border: none;
                padding: 18px 22px; /* 增大垂直内边距，让搜索框更有分量 */
                font-size: 24px; /* Spotlight 标志性的大字号 */
                font-weight: 500; /* 适中字重，比 Bold 更优雅 */
                font-family: "Segoe UI", "Microsoft YaHei UI", "SF Pro Display", sans-serif;
                letter-spacing: 0.5px;
            }
            
            /* 占位符样式：低调的灰色 */
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.35);
                font-weight: 400;
            }
            
            /* 选中文字的高亮色 */
            QLineEdit::selection {
                background-color: rgba(0, 100, 255, 0.6);
            }

            /* 3. 列表容器：透明背景，紧贴搜索框 */
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 6px 10px 10px 10px; /* 列表整体边距 */
            }
            
            /* 4. 列表项：舒展的高度，更合理的字体 */
            QListWidget::item {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.90);
                border-radius: 10px; /* 圆润的列表项 */
                margin-top: 4px;
                padding: 12px 14px; /* 增大垂直内边距 */
                font-size: 16px; /* 舒适的阅读字号 */
                font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
            }
            
            /* 选中与悬停效果：经典 macOS 阶梯蓝 */
            QListWidget::item:selected, QListWidget::item:hover {
                background-color: rgba(0, 99, 225, 0.85); /* macOS 选中的典型蓝色 */
                color: #FFFFFF;
            }
            
            /* 滚动条：极简风格 */
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.init_ui()

        # 创建粒子的绘制覆盖层
        self.particle_overlay = ParticleOverlay(self)
        self.particle_overlay.setGeometry(self.rect())
        self.particle_overlay.raise_()

        # 绑定事件
        self.search_input.textChanged.connect(self.on_text_changed)
        self.filter_apps("") # 初始刷新
        self.search_input.installEventFilter(self)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # 让背景样式完全控制边距
        self.layout.setSpacing(0)

        # 搜索输入框
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("🔍 搜索应用或按回车搜索网页...")
        self.search_input.setTextMargins(10, 0, 0, 0) # 微调图标与文字间距
        self.search_input.textChanged.connect(self.filter_apps)
        self.search_input.returnPressed.connect(self.launch_selected_app)
        self.layout.addWidget(self.search_input)

        # 搜索结果列表
        self.list_widget = QListWidget(self)
        self.list_widget.setIconSize(QSize(28, 28)) # 稍大的图标
        self.list_widget.setItemAlignment(Qt.AlignLeft)
        self.list_widget.itemClicked.connect(self.launch_selected_app)
        self.list_widget.itemDoubleClicked.connect(self.launch_selected_app)
        self.layout.addWidget(self.list_widget)
        self.list_widget.hide()

    def resizeEvent(self, event):
        """窗口调整大小时，确保粒子层同步覆盖全窗口"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_overlay'):
            self.particle_overlay.setGeometry(self.rect())

    def on_text_changed(self, text):
        """文本改变时在光标当前位置触发粒子轻柔扩散"""
        cursor_pos_in_input = self.search_input.cursorRect().center()
        burst_pos = self.search_input.mapTo(self, cursor_pos_in_input)
        self.particle_overlay.add_burst(QPointF(burst_pos.x(), burst_pos.y()), count=8)

    def eventFilter(self, obj, event):
        """事件过滤器：监控输入框的焦点事件"""
        if obj == self.search_input and event.type() == event.Type.FocusOut:
            QTimer.singleShot(10, self._ensure_focus)
        return super().eventFilter(obj, event)

    def _ensure_focus(self):
        """确保输入框保持焦点"""
        if self.isVisible():
            self.search_input.setFocus(Qt.OtherFocusReason)

    def filter_apps(self, text):
        """根据输入内容过滤列表"""
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

            # 匹配逻辑
            if (query in name.lower()) or (py_full and query in py_full) or (py_first and query in py_first):
                item = QListWidgetItem(icon, name) if icon else QListWidgetItem(name)
                item.setData(Qt.UserRole, path)
                self.list_widget.addItem(item)
                count += 1
                if count >= 10: break # 稍微增加显示条数

        if self.list_widget.count() > 0:
            self.list_widget.show()
            self.list_widget.setCurrentRow(0)
        else:
            self.list_widget.hide()
        self.adjustSize()

    def launch_selected_app(self):
        """启动选中的应用程序；若无选中应用，则使用系统默认浏览器搜索"""
        current_item = self.list_widget.currentItem()

        # 1. 优先启动本地应用
        if current_item and self.list_widget.isVisible():
            app_path = current_item.data(Qt.UserRole)
            if app_path and os.path.exists(app_path):
                try:
                    os.startfile(app_path)
                    self.close()
                    return
                except Exception as e:
                    print(f"启动本地应用失败: {e}")

        # 2. 无匹配时进行网页搜索
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
        """键盘事件处理"""
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
        """窗口关闭时清理"""
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
        self.cached_apps = [] # 缓存: [(app_name, full_path, QIcon, py_full, py_first), ...]
        self.signal_helper = HotkeySignalHelper()
        self.signal_helper.trigger_signal.connect(self.show_launcher)

        # 初始化时根据 key 读取配置
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
        """启用插件"""
        super().enable()
        self._start_hotkey_listener()
        if not self.cached_apps:
            threading.Thread(target=self._preload_apps, daemon=True).start()

    def disable(self):
        """禁用插件"""
        super().disable()
        self._stop_hotkey_listener()

    def _preload_apps(self):
        """后台预加载应用列表"""
        paths = [
            os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        ]
        found_names = set()
        apps_data = []
        icon_provider = QFileIconProvider()

        for base_path in paths:
            if not os.path.exists(base_path): continue
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith((".lnk", ".url")):
                        name = os.path.splitext(file)[0]
                        if "uninstall" in name.lower() or name in found_names:
                            continue
                        found_names.add(name)
                        full_path = os.path.join(root, file)
                        try:
                            icon = icon_provider.icon(QFileInfo(full_path))
                        except Exception:
                            icon = QIcon()

                        # 生成拼音索引
                        py_full, py_first = "", ""
                        if PYPINYIN_AVAILABLE:
                            py_full = "".join(lazy_pinyin(name)).lower()
                            py_first = "".join(lazy_pinyin(name, style=Style.FIRST_LETTER)).lower()

                        apps_data.append((name, full_path, icon, py_full, py_first))
        self.cached_apps = apps_data

    def _start_hotkey_listener(self):
        if not PYNPUT_AVAILABLE:
            print("[LauncherPlugin] 警告: 未安装 pynput，无法开启全局快捷键监听 (pip install pynput)")
            return
        self._stop_hotkey_listener()

        # 将快捷键映射更新为 Ctrl + Space
        hotkey_mapping = {
            '<ctrl>+<space>': self._on_hotkey_pressed
        }
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self.hotkey_listener.start()
        except Exception as e:
            print(f"[LauncherPlugin] 全局热键注册失败: {e}")

    def _stop_hotkey_listener(self):
        if self.hotkey_listener is not None:
            try: self.hotkey_listener.stop()
            except: pass
            self.hotkey_listener = None

    def _on_hotkey_pressed(self):
        self.signal_helper.trigger_signal.emit()

    def _force_focus_windows(self, hwnd):
        """Windows 平台强制获取焦点"""
        if sys.platform != 'win32' or not hwnd: return False
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
        if not self.is_enabled or not is_setting_enabled: return

        if self.dialog is not None:
            try:
                if self.dialog.isVisible():
                    self.dialog.activateWindow()
                    self.dialog.raise_()
                    if sys.platform == 'win32':
                        hwnd = get_window_handle(self.dialog)
                        if hwnd: self._force_focus_windows(hwnd)
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
        """延迟设置焦点"""
        if not self.dialog: return
        try:
            if not self.dialog.isVisible(): return
            self.dialog.activateWindow()
            self.dialog.raise_()
            self.dialog.search_input.setFocus(Qt.OtherFocusReason)
            self.dialog.search_input.selectAll()
            if not self.dialog.search_input.hasFocus() and sys.platform == 'win32':
                hwnd = get_window_handle(self.dialog.search_input)
                if hwnd: user32.SetFocus(hwnd)
        except RuntimeError:
            self.dialog = None

    def create_settings_widget(self, parent=None) -> QWidget:
        group = QGroupBox("🚀 快捷应用启动器", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        # 更新 UI 设置界面上的文字描述
        chk_enable = QCheckBox("启用 CTRL+SPACE 快捷唤起搜索框", group)
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