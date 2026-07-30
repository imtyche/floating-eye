import json
import time
import urllib.request
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QPoint
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QCheckBox, QGroupBox, QApplication, QGraphicsDropShadowEffect
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
                    "appKey": "heyjingway",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                try:
                    res_json = json.loads(res_body)

                    translated_text = None
                    if isinstance(res_json, dict) and "output" in res_json:
                        for item in res_json.get("output", []):
                            if item.get("type") == "message" and "content" in item:
                                for content_item in item.get("content", []):
                                    if content_item.get("type") == "output_text":
                                        translated_text = content_item.get("text")
                                        break
                            if translated_text:
                                break

                    if not translated_text:
                        translated_text = res_json.get('data') or res_json.get('result') or res_body

                except json.JSONDecodeError:
                    translated_text = res_body

                self.finished.emit(str(translated_text).strip())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            self.error.emit(f"HTTP {e.code}: {err_body if err_body else e.reason}")
        except Exception as e:
            self.error.emit(str(e))


class TranslationBubble(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 设置鼠标悬停为手型
        self.setCursor(Qt.PointingHandCursor)

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

    def show_message(self, text, duration=6000, pos=None):
        self.label.setText(text)
        self.adjustSize()
        if pos:
            self.move(pos)
        else:
            self.move(QCursor.pos() + QPoint(15, -self.height() - 15))
        self.show()
        self.hide_timer.start(duration)

    def mousePressEvent(self, event):
        """点击气泡任意位置直接关闭/隐藏"""
        if event.button() == Qt.LeftButton:
            self.hide_timer.stop()
            self.hide()
        super().mousePressEvent(event)


class TranslationPlugin(BasePlugin):
    """双击词汇延迟翻译插件（带打断功能）"""

    start_delay_signal = Signal()
    trigger_translation_signal = Signal()
    cancel_translation_signal = Signal()

    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.bubble = None
        self.worker = None

        self.mouse_listener = None
        self.kbd_listener = None

        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.double_click_interval = 0.4
        self.double_click_dist = 6

        # 标记是否正在执行系统级别的自动模拟按键(Ctrl+C)，避免误打断
        self._is_simulating_keypress = False

        # 3秒倒计时定时器
        self.delay_timer = QTimer(self)
        self.delay_timer.setSingleShot(True)
        self.delay_timer.setInterval(3000)  # 3000ms = 3秒
        self.delay_timer.timeout.connect(self._on_trigger_translation)

        # Qt 线程间信号绑定
        self.start_delay_signal.connect(self._on_start_delay)
        self.trigger_translation_signal.connect(self._on_trigger_translation)
        self.cancel_translation_signal.connect(self._on_cancel_translation)

    @property
    def plugin_id(self) -> str:
        return "ai_translation"

    @property
    def name(self) -> str:
        return "🤖 双击划词翻译"

    def enable(self):
        if self.is_enabled:
            return
        super().enable()
        if not self.bubble:
            self.bubble = TranslationBubble()

        # 启动鼠标与键盘监听器
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.mouse_listener.start()

        self.kbd_listener = keyboard.Listener(on_press=self._on_key_press)
        self.kbd_listener.start()

    def disable(self):
        if not self.is_enabled:
            return
        super().disable()

        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        if self.kbd_listener:
            self.kbd_listener.stop()
            self.kbd_listener = None

        self._on_cancel_translation()

    def _cleanup_worker(self):
        """安全停止并清理线程 worker"""
        if self.worker is not None:
            try:
                if self.worker.isRunning():
                    self.worker.terminate()
                    self.worker.wait(500)
            except RuntimeError:
                pass
            self.worker = None

    def _is_busy(self) -> bool:
        """检查当前是否处于倒计时等待中或正在翻译请求中"""
        timer_active = self.delay_timer.isActive()
        worker_active = self.worker is not None and self.worker.isRunning()
        return timer_active or worker_active

    def _on_mouse_click(self, x, y, button, pressed):
        if not self.is_enabled or not pressed:
            return

        current_time = time.time()
        dx = abs(x - self.last_click_pos[0])
        dy = abs(y - self.last_click_pos[1])

        # 判断是否构成双击
        if button == mouse.Button.left and (current_time - self.last_click_time) <= self.double_click_interval and dx <= self.double_click_dist and dy <= self.double_click_dist:
            self.last_click_time = 0
            # 触发 3 秒倒计时
            self.start_delay_signal.emit()
        else:
            self.last_click_time = current_time
            self.last_click_pos = (x, y)
            # 如果当前处于“3秒等待”或“翻译中”状态，任意鼠标点击都打断
            if self._is_busy():
                self.cancel_translation_signal.emit()

    def _on_key_press(self, key):
        if not self.is_enabled:
            return

        # 过滤模拟按键发出的触发
        if self._is_simulating_keypress:
            return

        # 如果处于“3秒等待”或“翻译中”状态，按下任意键盘按键打断翻译
        if self._is_busy():
            self.cancel_translation_signal.emit()

    def _on_start_delay(self):
        """开始 3 秒翻译倒计时"""
        self._on_cancel_translation()  # 取消之前的任务
        self.delay_timer.start()

    def _on_cancel_translation(self):
        """打断并取消当前等待和翻译任务"""
        # 停止倒计时
        if self.delay_timer.isActive():
            self.delay_timer.stop()

        # 终止正在发起的网络请求
        self._cleanup_worker()

        # 如果当前气泡正在显示“正在翻译中...”，隐藏气泡
        if self.bubble and self.bubble.isVisible():
            if "正在翻译" in self.bubble.label.text():
                self.bubble.hide()

    def _on_trigger_translation(self):
        """倒计时 3 秒结束后真正触发复制与翻译"""
        try:
            self._is_simulating_keypress = True
            kbd_controller = keyboard.Controller()
            kbd_controller.press(keyboard.Key.ctrl)
            kbd_controller.press('c')
            kbd_controller.release('c')
            kbd_controller.release(keyboard.Key.ctrl)
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            self._is_simulating_keypress = False

        QTimer.singleShot(150, self._process_clipboard_text)

    def _process_clipboard_text(self):
        clipboard = QApplication.clipboard()
        selected_text = clipboard.text().strip()

        if not selected_text:
            return

        self._cleanup_worker()

        self.bubble.show_message("🌐 正在翻译中...")

        self.worker = TranslationWorker(selected_text)
        self.worker.finished.connect(lambda res: self.bubble.show_message(f"🌐 翻译结果：\n{res}", 8000))
        self.worker.error.connect(lambda err: self.bubble.show_message(f"❌ 翻译失败:\n{err}", 4000))

        def _on_worker_finished():
            self.worker = None

        self.worker.destroyed.connect(_on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)

        self.worker.start()

    def create_settings_widget(self, parent=None) -> QWidget:
        group = QGroupBox("🤖 双击划词翻译插件", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        chk_enable = QCheckBox("启用双击划词翻译（双击选中3秒后翻译，按键/点击打断）", group)
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

        hint = QLabel("💡 使用提示：用鼠标双击选中文本后等待 3 秒会自动翻译；在等待或翻译期间点击鼠标或敲击键盘即可取消翻译。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888888; font-size: 11px; line-height: 1.4;")
        layout.addWidget(hint)

        return group