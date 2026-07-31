import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QSpinBox, QGroupBox, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor
from plugins.base import BasePlugin


class HealthyBubbleDialog(QWidget):
    """类似聊天气泡形式的健康提醒窗口"""

    def __init__(self, message="长时间工作啦，记得休息一下、喝杯水哦！", parent=None):
        super().__init__(parent)

        # 设置无边框、置顶、不抢占焦点的气泡样式
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        # 布局与 UI 初始化
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # 气泡容器
        bubble_frame = QWidget(self)
        bubble_frame.setStyleSheet("""
            QWidget {
                background-color: #2b2b36;
                color: #ffffff;
                border: 1px solid #444454;
                border-radius: 12px;
            }
        """)

        frame_layout = QVBoxLayout(bubble_frame)
        frame_layout.setContentsMargins(14, 10, 14, 10)

        # 提醒文本
        lbl_text = QLabel(message, bubble_frame)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
                border: none;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
            }
        """)
        frame_layout.addWidget(lbl_text)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        bubble_frame.setGraphicsEffect(shadow)

        layout.addWidget(bubble_frame)

        # 调整尺寸
        self.adjustSize()
        self.setFixedWidth(min(260, self.sizeHint().width()))

        # 定时器：显示 5 秒后自动关闭气泡
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(10000)

    def mousePressEvent(self, event):
        """点击气泡任意位置立即关闭"""
        self.close()


class HealthyPlugin(BasePlugin):
    """健康提醒插件"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_reminder)
        self.current_bubble = None

    @property
    def plugin_id(self) -> str:
        return "healthy_reminder"

    @property
    def name(self) -> str:
        return "🍵 健康休息提醒"

    def enable(self):
        super().enable()
        self._start_timer()

    def disable(self):
        super().disable()
        self.timer.stop()
        if self.current_bubble:
            self.current_bubble.close()

    def _start_timer(self):
        """启动或重置定时器"""
        if not self.is_enabled:
            return

        # 获取间隔时间设置（单位：分钟），默认 30 分钟
        interval_min_str = self.settings_manager.get_setting("plugin_healthy_interval", "30")
        try:
            interval_min = int(interval_min_str)
        except ValueError:
            interval_min = 30

        # 将分钟转为毫秒并启动定时器
        interval_ms = max(1, interval_min) * 60 * 1000
        self.timer.start(interval_ms)

    def show_reminder(self):
        """显示聊天气泡提醒"""
        if not self.is_enabled:
            return

        # 如果已有气泡显示，先关闭上一个
        if self.current_bubble:
            self.current_bubble.close()

        self.current_bubble = HealthyBubbleDialog(
            message="🍵 提示：您已经工作很长时间了，站起来活动一下，喝杯水吧！",
            parent=self.parent()
        )

        # 设置气泡在主窗口附近或屏幕右下角弹出
        if self.parent() and hasattr(self.parent(), "geometry"):
            parent_geom = self.parent().geometry()
            # 显示在父控件上方偏右位置
            x = parent_geom.x() + parent_geom.width() - 200
            y = max(20, parent_geom.y() - self.current_bubble.sizeHint().height() - 10)
            self.current_bubble.move(x, y)

        self.current_bubble.show()

    def create_settings_widget(self, parent=None) -> QWidget:
        """创建插件在设置界面中的配置 UI"""
        group = QGroupBox("🍵 健康提醒设置", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # 启用开关
        chk_enable = QCheckBox("启用定时健康休息提醒", group)
        is_enabled = self.settings_manager.get_setting("plugin_healthy_reminder_enabled", "false") == "true"
        chk_enable.setChecked(is_enabled)

        # 间隔时间设置栏
        interval_layout = QHBoxLayout()
        lbl_interval = QLabel("提醒间隔时间 (分钟):", group)

        spin_interval = QSpinBox(group)
        spin_interval.setRange(1, 180)  # 支持 1 ~ 180 分钟
        saved_interval = int(self.settings_manager.get_setting("plugin_healthy_interval", "30"))
        spin_interval.setValue(saved_interval)
        spin_interval.setEnabled(is_enabled)

        interval_layout.addWidget(lbl_interval)
        interval_layout.addWidget(spin_interval)
        interval_layout.addStretch()

        # 事件绑定：开启/关闭
        def on_toggle(checked):
            self.settings_manager.set_setting("plugin_healthy_reminder_enabled", "true" if checked else "false")
            spin_interval.setEnabled(checked)
            if checked:
                self.enable()
            else:
                self.disable()

        # 事件绑定：修改间隔时间
        def on_interval_changed(value):
            self.settings_manager.set_setting("plugin_healthy_interval", str(value))
            if self.is_enabled:
                self._start_timer()  # 更新定时器间隔

        chk_enable.toggled.connect(on_toggle)
        spin_interval.valueChanged.connect(on_interval_changed)

        layout.addWidget(chk_enable)
        layout.addLayout(interval_layout)

        return group