import json
import urllib.request
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QCheckBox, QGroupBox, QGraphicsDropShadowEffect
)
from pynput import mouse, keyboard
from plugins.base import BasePlugin


class TranslationWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text
        self.api_url = "https://alal.site/translate"

    def run(self):
        try:
            payload = {
                "targetLang": "中文",
                "data": self.text
            }
            data = json.dumps(payload).encode('utf-8')

            req = urllib.request.Request(
                self.api_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "appKey": "heyjingway"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                try:
                    res_json = json.loads(res_body)
                    translated_text = res_json.get('data') or res_json.get('result') or res_body
                except json.JSONDecodeError:
                    translated_text = res_body

                self.finished.emit(str(translated_text).strip())
        except Exception as e:
            self.error.emit(str(e))


class TranslationBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel("🤔 正在翻译中...", self)
        self.label.setWordWrap(True)
        self.label.setMaximumWidth(320)
        self.label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
                background-color: rgba(25, 25, 30, 0.92);
                border: 1px solid rgba(255, 60, 60, 0.5);
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        layout.addWidget(self.label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 4)
        self.label.setGraphicsEffect(shadow)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_message(self, text, duration=6000):
        self.label.setText(text)
        self.adjustSize()
        self.move(QCursor.pos() + QPoint(15, -self.height() - 15))
        self.show()
        self.hide_timer.start(duration)


class TranslationPlugin(BasePlugin):
    """划词翻译插件 - 线程安全的 3 秒自动触发模式"""

    # 🌟 定义自定义 Qt 信号，解决 pynput 线程与 Qt 主线程通讯问题
    drag_finished_signal = Signal()
    mouse_down_signal = Signal()
    trigger_translation_signal = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.bubble = None
        self.worker = None

        # 鼠标状态标记
        self.is_mouse_down = False
        self.has_dragged = False
        self.press_pos = (0, 0)

        # ⏱ 3秒延迟触发定时器（必须在 Qt 主线程创建与运行）
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._on_idle_timeout)

        self.mouse_listener = None

        # 信号与主线程槽函数绑定
        self.drag_finished_signal.connect(self._start_idle_timer)
        self.mouse_down_signal.connect(self._stop_idle_timer)
        self.trigger_translation_signal.connect(self._on_trigger_translation)

    @property
    def plugin_id(self) -> str:
        return "ai_translation"

    @property
    def name(self) -> str:
        return "🤖 划词翻译"

    def enable(self):
        if self.is_enabled:
            return
        super().enable()
        if not self.bubble:
            self.bubble = TranslationBubble()

        # 启动全局鼠标监听
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
            on_move=self._on_mouse_move
        )
        self.mouse_listener.start()

    def disable(self):
        if not self.is_enabled:
            return
        super().disable()
        self._stop_idle_timer()

        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        if self.bubble:
            self.bubble.hide()

    def _on_mouse_click(self, x, y, button, pressed):
        """pynput 独立子线程中运行的鼠标点击回调"""
        if not self.is_enabled:
            return

        if button == mouse.Button.left:
            if pressed:
                self.is_mouse_down = True
                self.has_dragged = False
                self.press_pos = (x, y)
                # 发送信号停止之前的定时器
                self.mouse_down_signal.emit()
            else:
                self.is_mouse_down = False
                # 产生拖拽距离大于 10 像素才判定为有效的“划词”
                if self.has_dragged:
                    self.has_dragged = False
                    # 发送信号让主线程开启 3 秒计时器
                    self.drag_finished_signal.emit()

    def _on_mouse_move(self, x, y):
        """pynput 独立子线程中运行的鼠标移动回调"""
        if not self.is_enabled or not self.is_mouse_down:
            return

        if abs(x - self.press_pos[0]) > 10 or abs(y - self.press_pos[1]) > 10:
            self.has_dragged = True

    # ==========================================
    # 🌟 下面是跑在 Qt 主线程的槽函数
    # ==========================================
    def _start_idle_timer(self):
        """主线程槽：启动 3000ms 倒计时"""
        if self.is_enabled:
            self.idle_timer.start(3000)

    def _stop_idle_timer(self):
        """主线程槽：停止倒计时"""
        self.idle_timer.stop()

    def _on_idle_timeout(self):
        """倒计时 3 秒结束，发送触发翻译信号"""
        if self.is_enabled:
            self.trigger_translation_signal.emit()

    def _on_trigger_translation(self):
        """在主线程模拟 Ctrl+C 复制选中文本"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        old_text = clipboard.text()

        # 模拟键盘按下 Ctrl + C 复制选中的文本
        try:
            kbd_controller = keyboard.Controller()
            with kbd_controller.pressed(keyboard.Key.ctrl):
                kbd_controller.press('c')
                kbd_controller.release('c')
        except Exception as e:
            print(f"模拟复制快捷键异常: {e}")

        # 延迟 200ms 等待系统剪贴板更新数据
        QTimer.singleShot(200, lambda: self._process_clipboard_text(old_text))

    def _process_clipboard_text(self, old_text):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        selected_text = clipboard.text().strip()

        # 过滤无效文本
        if not selected_text or selected_text == old_text.strip() or len(selected_text) > 800:
            return

        self.bubble.show_message("🌐 正在翻译中...")
        self.worker = TranslationWorker(selected_text)
        self.worker.finished.connect(lambda res: self.bubble.show_message(f"🌐 翻译结果：\n{res}", 8000))
        self.worker.error.connect(lambda err: self.bubble.show_message(f"❌ 翻译失败:\n{err}", 4000))
        self.worker.start()

    # ==========================================
    # 🌟 插件设置 UI
    # ==========================================
    def create_settings_widget(self, parent=None) -> QWidget:
        group = QGroupBox("🤖 划词翻译插件", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        chk_enable = QCheckBox("启用自动划词翻译（划词松开 3 秒后自动翻译）", group)
        is_enabled = self.settings_manager.get_setting("plugin_ai_translation_enabled", "false") == "true"
        chk_enable.setChecked(is_enabled)

        def on_toggle(checked):
            self.settings_manager.set_setting("plugin_ai_translation_enabled", "true" if checked else "false")
            if checked:
                self.enable()
            else:
                self.disable()

        chk_enable.toggled.connect(on_toggle)
        layout.addWidget(chk_enable)

        hint = QLabel("💡 测试提示：用鼠标按住左键拖拽选中一段文字，松开鼠标后静置 3 秒，即可自动展示翻译浮窗。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.4;")
        layout.addWidget(hint)

        return group