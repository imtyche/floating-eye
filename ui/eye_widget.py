import os
import math
import random
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QRegion, QPainterPath, QAction
from PySide6.QtWidgets import QWidget, QApplication, QMenu

from plugins.manager import PluginManager

# 设置 Qt 环境
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from config.themes import ThemeManager
from core.database import DatabaseManager
from core.settings import SettingsManager
from monitoring.monitor_thread import MonitorThread


class FloatingEye(QWidget):
    """浮空眼睛主窗口 - 带有动态眼睛动画效果及双推进器"""

    def __init__(self):
        super().__init__()
        MYSQL_CONFIG = {
            'host': 'a.alal.site',
            'port': 3306,
            'user': 'root',
            'password': 'shujuku129!',
            'database': 'activity_db',
            'charset': 'utf8mb4'
        }
        # 初始化核心组件
        self.db = DatabaseManager(MYSQL_CONFIG)
        self.settings_manager = SettingsManager(MYSQL_CONFIG)

        # 1. 创建 PluginManager
        self.plugin_manager = PluginManager(self.settings_manager, self)

        # 2. 自动开启先前已勾选启用的插件
        self.plugin_manager.load_all_plugins()

        # 加载设置
        self.load_settings()

        # 初始化监控线程
        self.monitor = MonitorThread(self.settings_manager)
        self.monitor.activity_changed.connect(self.on_activity_changed)
        self.monitor.start()

        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 稍微增大窗口高度以容纳下方的推进器火焰
        self.resize(70, 70)

        # 拖拽相关
        self.drag_position = QPoint()

        # 眼球位置相关
        self.eye_x = 0.0
        self.eye_y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0

        # 鼠标闲置检测
        self.last_mouse_pos = QPoint()
        self.mouse_idle_counter = 0
        self.mouse_idle_threshold = 180
        self.is_mouse_idle = False

        # 偷看逻辑相关
        self.is_glancing = False
        self.glance_target_x = 0.0
        self.glance_target_y = 0.0
        self.glance_timer = 0
        self.next_glance_delay = random.randint(100, 300)
        self.glance_duration = 0

        # 动画相关
        self.glow_pulse = 0.0
        self.vein_throb = 0.0
        self.pupil_dilate = 1.0
        self.tremor_phase = random.uniform(0, 2 * math.pi)
        self.blink_progress = 0.0
        self.is_blinking = False
        self.blink_timer = 0
        self.next_blink_delay = random.randint(300, 600)
        self.iris_rotation = 0.0
        self.vein_phase = 0.0
        self.blink_phase = 0

        # ===== 浮动效果相关 =====
        self.float_phase = random.uniform(0, 2 * math.pi)
        self.float_offset_y = 0.0
        self.float_amplitude = 4.0
        self.float_speed = 0.025

        # ===== 推进器效果相关 =====
        self.booster_flame_phase = 0.0

        # 动画定时器 (约60FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

        # 启用鼠标追踪
        self.setMouseTracking(True)

        # 应用开机启动设置
        self.apply_auto_start()

    def load_settings(self):
        """加载设置"""
        self.use_camera = self.settings_manager.get_setting('use_camera', 'true') == 'true'
        self.use_screenshot = self.settings_manager.get_setting('use_screenshot', 'true') == 'true'
        self.capture_interval = int(self.settings_manager.get_setting('capture_interval', '3'))
        self.auto_start = self.settings_manager.get_setting('auto_start', 'false') == 'true'
        self.current_theme = self.settings_manager.get_setting('theme', 'blood')
        self.eye_color_mode = self.settings_manager.get_setting('eye_color', 'default')
        self.retention_days = self.settings_manager.get_setting('retention_days', '0')
        self.db.clean_expired_logs(self.retention_days)

    def apply_settings(self):
        """应用设置（从设置对话框调用）"""
        self.load_settings()
        if self.monitor:
            self.monitor.update_settings()
        self.apply_auto_start()
        self.update()

    def apply_auto_start(self):
        """应用开机启动设置"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "FloatingEye"

            if self.auto_start:
                import sys
                exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__

                if not getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}" "{__file__}"'
                else:
                    exe_path = f'"{exe_path}"'

                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                    winreg.CloseKey(key)
                except Exception as e:
                    print(f"⚠️ 添加开机启动失败: {e}")
            else:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, app_name)
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"⚠️ 移除开机启动失败: {e}")
        except ImportError:
            print("⚠️ 不支持当前平台的开机启动设置")

    def on_activity_changed(self, title, screenshot_base64):
        """处理活动窗口变化"""
        self.db.add_log(title, screenshot_base64, retention_days=self.retention_days)

    def create_eye_shape(self, cx, cy, w, h):
        """创建眼睛形状路径"""
        path = QPainterPath()
        path.moveTo(cx + w, cy)
        path.quadTo(cx + w * 0.5, cy - h, cx, cy - h * 1.05)
        path.quadTo(cx - w * 0.5, cy - h, cx - w, cy)
        path.quadTo(cx - w * 0.5, cy + h * 0.7, cx, cy + h * 0.8)
        path.quadTo(cx + w * 0.5, cy + h * 0.7, cx + w, cy)
        path.closeSubpath()
        return path

    def update_animation(self):
        """更新动画状态"""
        global_cursor = self.cursor().pos()
        local_cursor = self.mapFromGlobal(global_cursor)

        center_x, center_y = 35, 28
        max_radius_x = 13
        max_radius_y = 9
        current_mouse_pos = local_cursor

        # 鼠标移动检测
        if current_mouse_pos != self.last_mouse_pos:
            self.mouse_idle_counter = 0
            self.is_mouse_idle = False
            self.is_glancing = False
            self.glance_timer = 0
            self.last_mouse_pos = current_mouse_pos
        else:
            if not self.is_mouse_idle:
                self.mouse_idle_counter += 1
                if self.mouse_idle_counter >= self.mouse_idle_threshold:
                    self.is_mouse_idle = True
                    self.mouse_idle_counter = 0

        # 计算眼球目标位置
        if self.is_mouse_idle:
            self.glance_timer += 1
            if not self.is_glancing:
                if self.glance_timer >= self.next_glance_delay:
                    self.is_glancing = True
                    self.glance_timer = 0
                    self.glance_duration = random.randint(40, 120)

                    direction = random.choice(['up', 'down', 'left', 'right'])
                    if direction == 'up':
                        self.glance_target_x, self.glance_target_y = 0.0, -10.0
                    elif direction == 'down':
                        self.glance_target_x, self.glance_target_y = 0.0, 8.0
                    elif direction == 'left':
                        self.glance_target_x, self.glance_target_y = -11.0, 0.0
                    elif direction == 'right':
                        self.glance_target_x, self.glance_target_y = 11.0, 0.0
            else:
                if self.glance_timer >= self.glance_duration:
                    self.is_glancing = False
                    self.glance_timer = 0
                    self.next_glance_delay = random.randint(150, 400)

            base_target_x = self.glance_target_x if self.is_glancing else 0.0
            base_target_y = self.glance_target_y if self.is_glancing else 0.0
        else:
            base_target_x = (local_cursor.x() - center_x) / 5.0
            base_target_y = (local_cursor.y() - center_y) / 6.0

            distance = math.sqrt((base_target_x / max_radius_x)**2 + (base_target_y / max_radius_y)**2)
            if distance > 1:
                scale = 1 / distance
                base_target_x *= scale
                base_target_y *= scale

        tremor_scale = 0.05 if self.is_glancing else 0.12
        self.tremor_phase += 0.06
        tremor_x = math.sin(self.tremor_phase) * tremor_scale
        tremor_y = math.cos(self.tremor_phase * 0.7 + 1.2) * tremor_scale

        self.target_x = base_target_x + tremor_x
        self.target_y = base_target_y + tremor_y

        self.eye_x += (self.target_x - self.eye_x) * 0.08
        self.eye_y += (self.target_y - self.eye_y) * 0.08

        # ===== 浮动与推进器相位动画 =====
        self.float_phase += self.float_speed
        self.float_offset_y = math.sin(self.float_phase) * self.float_amplitude
        self.booster_flame_phase += 0.35  # 火焰波动速度

        # 更新其他动画参数
        self.iris_rotation += 0.0008
        self.glow_pulse += 0.03
        self.vein_phase += 0.02
        self.vein_throb = 0.5 + 0.5 * math.sin(self.vein_phase)
        self.pupil_dilate = 0.9 + 0.1 * math.sin(self.glow_pulse * 0.5)

        # 眨眼逻辑
        self.blink_timer += 1
        if not self.is_blinking:
            if self.blink_timer >= self.next_blink_delay:
                self.is_blinking = True
                self.blink_progress = 0.0
                self.blink_phase = 1
                self.next_blink_delay = random.randint(200, 500)
                self.blink_timer = 0
        else:
            speed = 0.06
            if self.blink_phase == 1:
                self.blink_progress += speed
                if self.blink_progress >= 1.0:
                    self.blink_progress = 1.0
                    self.blink_phase = 2
            elif self.blink_phase == 2:
                self.blink_timer += 1
                if self.blink_timer >= 3:
                    self.blink_timer = 0
                    self.blink_phase = 3
            elif self.blink_phase == 3:
                self.blink_progress -= speed
                if self.blink_progress <= 0.0:
                    self.blink_progress = 0.0
                    self.is_blinking = False
                    self.blink_phase = 0
                    self.blink_timer = 0

        self.update()

    def draw_boosters(self, painter, center_x, center_y):
        """绘制眼睛下方外八字斜向喷射的两个推进器及动态火焰"""
        # 左右喷喷嘴的位置与倾斜角度（角度：左喷嘴顺时针偏转，右喷嘴逆时针偏转）
        booster_configs = [
            {'x': center_x - 20, 'y': center_y + 16, 'angle': 25.0},  # 左推进器：向左外八字倾斜
            {'x': center_x + 20, 'y': center_y + 16, 'angle': -25.0}   # 右推进器：向右外八字倾斜
        ]

        nozzle_w = 7
        nozzle_h = 8

        # 确定火焰颜色梯度 (跟随 eye_color_mode 主题)
        if self.eye_color_mode == 'angel':
            core_color = QColor(200, 240, 255, 230)
            mid_color = QColor(0, 150, 255, 180)
            outer_color = QColor(0, 50, 200, 0)
        elif self.eye_color_mode == 'demon':
            core_color = QColor(240, 200, 255, 230)
            mid_color = QColor(160, 0, 220, 180)
            outer_color = QColor(60, 0, 120, 0)
        else:  # default (Blood)
            core_color = QColor(255, 220, 150, 230)
            mid_color = QColor(255, 60, 0, 180)
            outer_color = QColor(180, 0, 0, 0)

        for idx, config in enumerate(booster_configs):
            painter.save()

            # 将坐标系平移至喷嘴中心并旋转，实现八字散开的效果
            painter.translate(config['x'], config['y'])
            painter.rotate(config['angle'])

            # ===== 1. 绘制喷气火焰 =====
            noise = random.uniform(-1.5, 1.5)
            flame_len = 14 + math.sin(self.booster_flame_phase + idx) * 3.5 + noise
            flame_w = nozzle_w * (0.85 + math.sin(self.booster_flame_phase * 1.5) * 0.1)

            flame_path = QPainterPath()
            flame_top = nozzle_h / 2
            flame_path.moveTo(-flame_w / 2, flame_top)
            flame_path.quadTo(0, flame_top + flame_len * 1.2, flame_w / 2, flame_top)
            flame_path.closeSubpath()

            flame_grad = QLinearGradient(0, flame_top, 0, flame_top + flame_len)
            flame_grad.setColorAt(0.0, core_color)
            flame_grad.setColorAt(0.4, mid_color)
            flame_grad.setColorAt(1.0, outer_color)

            painter.setPen(Qt.NoPen)
            painter.setBrush(flame_grad)
            painter.drawPath(flame_path)

            # ===== 2. 绘制金属喷嘴外壳 =====
            nozzle_path = QPainterPath()
            nozzle_path.moveTo(-nozzle_w / 2 + 1, -nozzle_h / 2)
            nozzle_path.lineTo(nozzle_w / 2 - 1, -nozzle_h / 2)
            nozzle_path.lineTo(nozzle_w / 2, nozzle_h / 2)
            nozzle_path.lineTo(-nozzle_w / 2, nozzle_h / 2)
            nozzle_path.closeSubpath()

            nozzle_grad = QLinearGradient(-nozzle_w / 2, 0, nozzle_w / 2, 0)
            nozzle_grad.setColorAt(0.0, QColor(40, 40, 45))
            nozzle_grad.setColorAt(0.5, QColor(110, 110, 120))
            nozzle_grad.setColorAt(1.0, QColor(30, 30, 35))

            painter.setBrush(nozzle_grad)
            painter.setPen(QColor(20, 20, 25))
            painter.drawPath(nozzle_path)

            painter.restore()

    def paintEvent(self, event):
        """绘制眼睛与推进器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # ===== 应用浮动偏移到中心位置 =====
        center_x = 35
        center_y = 28 + self.float_offset_y

        # 1. 优先绘制下方的双推进器（置于眼睛图层下方）
        self.draw_boosters(painter, center_x, center_y)

        socket_w = 30
        socket_h = 22

        # 眨眼效果
        blink_factor = self.blink_progress
        height_scale = 1.0 - blink_factor * 0.85
        current_h = socket_h * height_scale
        if current_h < 1.0:
            current_h = 1.0

        # 2. 绘制眼窝形状
        eye_path = self.create_eye_shape(center_x, center_y, socket_w, current_h)

        # 绘制眼窝背景
        socket_grad = QRadialGradient(center_x, center_y + 2, socket_w)
        socket_grad.setColorAt(0.0, QColor(15, 5, 8, 255))
        socket_grad.setColorAt(0.3, QColor(10, 3, 5, 255))
        socket_grad.setColorAt(0.7, QColor(8, 2, 4, 255))
        socket_grad.setColorAt(0.9, QColor(5, 1, 2, 255))
        socket_grad.setColorAt(1.0, QColor(2, 0, 1, 255))
        painter.setPen(Qt.NoPen)
        painter.setBrush(socket_grad)
        painter.drawPath(eye_path)

        # 绘制外部发光
        glow_w = socket_w + 5 + 2 * math.sin(self.glow_pulse)
        glow_h = socket_h + 3 + 2 * math.sin(self.glow_pulse)
        glow_path = self.create_eye_shape(center_x, center_y, glow_w, glow_h)
        glow_grad = QRadialGradient(center_x, center_y, glow_w)

        glow_colors = {
            'default': [
                (0.0, QColor(255, 0, 0, 0)),
                (0.5, QColor(200, 0, 0, 0)),
                (0.75, QColor(150, 0, 0, 8)),
                (0.9, QColor(100, 0, 0, 20)),
                (1.0, QColor(50, 0, 0, 35))
            ],
            'angel': [
                (0.0, QColor(0, 100, 255, 0)),
                (0.5, QColor(0, 80, 200, 0)),
                (0.75, QColor(0, 60, 150, 8)),
                (0.9, QColor(0, 40, 100, 20)),
                (1.0, QColor(0, 20, 50, 35))
            ],
            'demon': [
                (0.0, QColor(128, 0, 128, 0)),
                (0.5, QColor(100, 0, 100, 0)),
                (0.75, QColor(80, 0, 80, 8)),
                (0.9, QColor(60, 0, 60, 20)),
                (1.0, QColor(30, 0, 30, 35))
            ]
        }

        current_glow_stops = glow_colors.get(self.eye_color_mode, glow_colors['default'])
        for stop, color in current_glow_stops:
            glow_grad.setColorAt(stop, color)
        painter.setBrush(glow_grad)
        painter.drawPath(glow_path)

        painter.save()
        painter.setClipPath(eye_path)

        # 绘制眼白（巩膜）
        eye_radius_x = socket_w * 0.82
        eye_radius_y = current_h * 0.78
        if eye_radius_y < 3:
            eye_radius_y = 3

        eye_center_x = center_x + self.eye_x * 0.6
        eye_center_y = center_y + self.eye_y * 0.6

        sclera_grad = QRadialGradient(eye_center_x - 1, eye_center_y - 1, eye_radius_x)

        if self.eye_color_mode == 'angel':
            sclera_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
            sclera_grad.setColorAt(0.5, QColor(245, 245, 255, 235))
            sclera_grad.setColorAt(0.8, QColor(230, 235, 245, 230))
            sclera_grad.setColorAt(1.0, QColor(210, 215, 230, 220))
        else:
            sclera_grad.setColorAt(0.0, QColor(70, 55, 55, 240))
            sclera_grad.setColorAt(0.5, QColor(55, 42, 42, 235))
            sclera_grad.setColorAt(0.8, QColor(40, 30, 30, 230))
            sclera_grad.setColorAt(1.0, QColor(25, 18, 18, 220))

        painter.setBrush(sclera_grad)
        painter.drawEllipse(QRectF(eye_center_x - eye_radius_x, eye_center_y - eye_radius_y,
                                   eye_radius_x * 2, eye_radius_y * 2))

        # 绘制虹膜
        iris_x = eye_center_x + self.eye_x * 0.8
        iris_y = eye_center_y + self.eye_y * 0.8
        iris_radius_x = 13
        iris_radius_y = 12
        iris_scale = 1.0 - blink_factor * 0.5
        iris_radius_x *= iris_scale
        iris_radius_y *= iris_scale

        iris_grad = QRadialGradient(iris_x - 1, iris_y - 1, iris_radius_x)

        if self.eye_color_mode == 'angel':
            iris_grad.setColorAt(0.0, QColor(100, 200, 255))
            iris_grad.setColorAt(0.2, QColor(0, 150, 220))
            iris_grad.setColorAt(0.4, QColor(0, 100, 180))
            iris_grad.setColorAt(0.6, QColor(0, 80, 150))
            iris_grad.setColorAt(0.8, QColor(0, 50, 100))
            iris_grad.setColorAt(1.0, QColor(0, 20, 50))
        elif self.eye_color_mode == 'demon':
            iris_grad.setColorAt(0.0, QColor(200, 100, 255))
            iris_grad.setColorAt(0.2, QColor(160, 0, 200))
            iris_grad.setColorAt(0.4, QColor(120, 0, 160))
            iris_grad.setColorAt(0.6, QColor(80, 0, 100))
            iris_grad.setColorAt(0.8, QColor(40, 0, 60))
            iris_grad.setColorAt(1.0, QColor(20, 0, 30))
        else:
            iris_grad.setColorAt(0.0, QColor(180, 0, 0))
            iris_grad.setColorAt(0.2, QColor(140, 0, 0))
            iris_grad.setColorAt(0.4, QColor(100, 0, 0))
            iris_grad.setColorAt(0.6, QColor(70, 0, 0))
            iris_grad.setColorAt(0.8, QColor(40, 0, 0))
            iris_grad.setColorAt(1.0, QColor(15, 0, 0))

        painter.setBrush(iris_grad)
        painter.drawEllipse(QRectF(iris_x - iris_radius_x, iris_y - iris_radius_y,
                                   iris_radius_x * 2, iris_radius_y * 2))

        # 绘制瞳孔
        pupil_w = 3.0 * self.pupil_dilate
        pupil_h = 8.0 * self.pupil_dilate
        pupil_scale = 1.0 - blink_factor * 0.6
        pupil_w *= pupil_scale
        pupil_h *= pupil_scale

        pupil_grad = QRadialGradient(iris_x, iris_y, pupil_h)

        if self.eye_color_mode == 'angel':
            pupil_grad.setColorAt(0.0, QColor(0, 0, 0, 255))
            pupil_grad.setColorAt(0.7, QColor(0, 20, 40, 250))
            pupil_grad.setColorAt(1.0, QColor(0, 50, 80, 240))
        elif self.eye_color_mode == 'demon':
            pupil_grad.setColorAt(0.0, QColor(0, 0, 0, 255))
            pupil_grad.setColorAt(0.7, QColor(30, 0, 30, 250))
            pupil_grad.setColorAt(1.0, QColor(60, 0, 60, 240))
        else:
            pupil_grad.setColorAt(0.0, QColor(0, 0, 0, 255))
            pupil_grad.setColorAt(0.7, QColor(0, 0, 0, 250))
            pupil_grad.setColorAt(1.0, QColor(30, 0, 0, 240))

        painter.setBrush(pupil_grad)
        painter.drawRoundedRect(
            QRectF(iris_x - pupil_w/2, iris_y - pupil_h/2, pupil_w, pupil_h),
            1, 1
        )

        # 高光
        highlight_alpha = int(120 * (1.0 - blink_factor * 0.8))
        if highlight_alpha > 0:
            highlight_grad = QRadialGradient(iris_x - 3, iris_y - 4, 3)
            highlight_grad.setColorAt(0.0, QColor(255, 255, 255, highlight_alpha))
            highlight_grad.setColorAt(0.5, QColor(255, 255, 255, highlight_alpha // 2))
            highlight_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(highlight_grad)
            painter.drawEllipse(QRectF(iris_x - 5, iris_y - 6, 5, 5))

        painter.restore()
        painter.end()

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        try:
            if event.button() == Qt.LeftButton:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            elif event.button() == Qt.RightButton:
                self.show_context_menu(event.globalPosition().toPoint())
        except Exception as e:
            print(f"鼠标事件错误: {e}")

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        try:
            if event.buttons() == Qt.LeftButton:
                self.move(event.globalPosition().toPoint() - self.drag_position)
        except Exception as e:
            print(f"鼠标移动错误: {e}")

    def mouseDoubleClickEvent(self, event):
        """鼠标双击眼睛事件"""
        if event.button() == Qt.LeftButton:
            # 查找并触发待办事项插件
            todo_plugin = self.plugin_manager.plugins.get("todo_list")
            if todo_plugin and todo_plugin.is_enabled:
                todo_plugin.show_todo_dialog()
        super().mouseDoubleClickEvent(event)

    def show_context_menu(self, pos):
        """显示右键菜单"""
        try:
            menu = QMenu(self)
            colors = ThemeManager.get_colors(self.current_theme)

            menu.setStyleSheet(f"""
            QMenu {{
                background-color: rgba({self._hex_to_rgb(colors['bg_primary'])}, 0.95);
                color: {colors['text_primary']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {colors['highlight']};
            }}
            """)

            settings_action = QAction("⚙️ 设置", self)
            settings_action.triggered.connect(self.open_settings_dialog)
            menu.addAction(settings_action)

            logs_action = QAction("👁 查看活动历史", self)
            logs_action.triggered.connect(self.open_log_dialog)
            menu.addAction(logs_action)

            menu.addSeparator()

            quit_action = QAction("💀 退出", self)
            quit_action.triggered.connect(self.quit_app)
            menu.addAction(quit_action)

            menu.exec(pos)
        except Exception as e:
            print(f"显示菜单错误: {e}")

    def _hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为 RGB 字符串"""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}"
        return "10, 0, 0"

    def open_settings_dialog(self):
        """打开设置对话框"""
        try:
            from ui.dialogs import SettingsDialog
            dialog = SettingsDialog(self.settings_manager, self)
            dialog.exec()
            self.current_theme = self.settings_manager.get_setting('theme', 'blood')
        except Exception as e:
            print(f"打开设置对话框错误: {e}")

    def open_log_dialog(self):
        """打开日志对话框"""
        try:
            from ui.dialogs import LogDialog
            dialog = LogDialog(self.db, self)
            dialog.exec()
        except Exception as e:
            print(f"打开日志对话框错误: {e}")

    def quit_app(self):
        """退出应用"""
        try:
            self.monitor.stop()
            QApplication.quit()
        except Exception as e:
            print(f"退出错误: {e}")