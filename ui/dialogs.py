from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (
    QApplication,  # 添加这个导入
    QDialog, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QDateEdit, QComboBox, QFrame,
    QScrollArea, QCheckBox, QSpinBox, QGroupBox,
    QButtonGroup, QMessageBox, QListWidget, QSizePolicy, QWidget, QSpacerItem
)
from config.themes import ThemeManager
from ui.theme_style import ThemeStyleGenerator
from capture.screenshot import ScreenshotManager, QT_MULTIMEDIA_AVAILABLE


class ImageViewDialog(QDialog):
    """图片查看对话框"""

    def __init__(self, pixmap, title="查看截图", parent=None, theme='blood'):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(600, 500)

        colors = ThemeManager.get_colors(theme)
        self.setStyleSheet(f"""
        QDialog {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 8px;
        }}
        QLabel {{
            color: {colors['text_primary']};
        }}
        QPushButton {{
            background-color: {colors['bg_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 20px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {colors['bg_hover']};
            border-color: {colors['border_hover']};
        }}
        QScrollArea {{
            border: none;
            background-color: {colors['bg_primary']};
        }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("📷 " + title)
        title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['title']};")
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"background-color: {colors['bg_primary']}; padding: 10px;")

        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(560, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.setToolTip("双击查看原图")
        else:
            self.image_label.setText("📭 图片加载失败")
            self.image_label.setStyleSheet(f"color: {colors['text_muted']}; font-size: 14px;")

        scroll.setWidget(self.image_label)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.parent = parent

        # 加载当前主题
        self.current_theme = self.settings_manager.get_setting('theme', 'blood')

        self.setWindowTitle("⚙️ 设置")
        self.resize(480, 580)
        self.setModal(True)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center() - self.rect().center())

        self.init_ui()
        self.load_settings()
        self.apply_theme()

    def apply_theme(self):
        """应用当前主题"""
        style = ThemeStyleGenerator.get_dialog_style(self.current_theme)
        self.setStyleSheet(style)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(25, 20, 25, 25)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setProperty("class", "title-label")
        main_layout.addWidget(title)

        # 分隔线
        sep = QFrame()
        sep.setProperty("class", "separator")
        sep.setFrameShape(QFrame.HLine)
        main_layout.addWidget(sep)
        main_layout.addSpacing(10)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(0, 0, 10, 0)

        # 1. 主题设置
        theme_group = QGroupBox("🎨 界面主题")
        theme_layout = QVBoxLayout()
        theme_layout.setSpacing(12)
        theme_layout.setContentsMargins(15, 20, 15, 15)

        theme_widget = QWidget()
        theme_widget_layout = QHBoxLayout(theme_widget)
        theme_widget_layout.setContentsMargins(0, 0, 0, 0)
        theme_widget_layout.setSpacing(12)

        theme_label = QLabel("选择主题：")
        theme_label.setStyleSheet("font-weight: bold;")
        theme_widget_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        theme_order = ['dark', 'light', 'blood']
        for key in theme_order:
            self.theme_combo.addItem(ThemeManager.get_theme_name(key), key)
        self.theme_combo.setToolTip("切换界面主题风格")
        theme_widget_layout.addWidget(self.theme_combo)
        theme_widget_layout.addStretch()

        theme_layout.addWidget(theme_widget)

        theme_hint = QLabel("💡 主题将应用于设置、历史记录等所有界面")
        theme_hint.setProperty("class", "hint")
        theme_layout.addWidget(theme_hint)

        theme_group.setLayout(theme_layout)
        scroll_layout.addWidget(theme_group)

        # 2. 捕获设置
        capture_group = QGroupBox("📷 捕获设置")
        capture_layout = QVBoxLayout()
        capture_layout.setSpacing(12)
        capture_layout.setContentsMargins(15, 20, 15, 15)

        self.use_camera_check = QCheckBox("启用相机拍摄（优先）")
        self.use_camera_check.setToolTip("启用后优先使用摄像头拍照，失败时自动切换截图")
        capture_layout.addWidget(self.use_camera_check)

        self.use_screenshot_check = QCheckBox("启用屏幕截图（备用）")
        self.use_screenshot_check.setToolTip("相机不可用时自动使用屏幕截图")
        capture_layout.addWidget(self.use_screenshot_check)

        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 8, 0, 8)
        interval_layout.setSpacing(12)

        interval_label = QLabel("捕获间隔：")
        interval_label.setStyleSheet("font-weight: bold; min-width: 80px;")
        interval_layout.addWidget(interval_label)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 20)
        self.interval_spin.setValue(3)
        self.interval_spin.setToolTip("每切换 N 个窗口触发一次捕获")
        interval_layout.addWidget(self.interval_spin)

        interval_unit = QLabel("个窗口")
        interval_unit.setStyleSheet("color: #888888;")
        interval_layout.addWidget(interval_unit)
        interval_layout.addStretch()

        capture_layout.addWidget(interval_widget)

        hint = QLabel("💡 相机优先，失败时自动切换到截图模式")
        hint.setProperty("class", "hint")
        capture_layout.addWidget(hint)

        capture_group.setLayout(capture_layout)
        scroll_layout.addWidget(capture_group)

        # 3. 眼睛颜色设置
        eye_color_group = QGroupBox("👁 眼睛颜色")
        eye_color_layout = QVBoxLayout()
        eye_color_layout.setSpacing(12)
        eye_color_layout.setContentsMargins(15, 20, 15, 15)

        eye_color_widget = QWidget()
        eye_color_widget_layout = QHBoxLayout(eye_color_widget)
        eye_color_widget_layout.setContentsMargins(0, 0, 0, 0)
        eye_color_widget_layout.setSpacing(10)

        self.eye_color_default = QCheckBox("默认（血红）")
        self.eye_color_default.setToolTip("当前经典的血色眼睛")
        self.eye_color_angel = QCheckBox("天使（蔚蓝）")
        self.eye_color_angel.setToolTip("神圣的蓝色眼睛")
        self.eye_color_demon = QCheckBox("恶魔（暗紫）")
        self.eye_color_demon.setToolTip("深渊的紫色眼睛")

        # 使用 ButtonGroup 实现互斥
        self.eye_color_group = QButtonGroup(self)
        self.eye_color_group.addButton(self.eye_color_default, 1)
        self.eye_color_group.addButton(self.eye_color_angel, 2)
        self.eye_color_group.addButton(self.eye_color_demon, 3)

        eye_color_widget_layout.addWidget(self.eye_color_default)
        eye_color_widget_layout.addWidget(self.eye_color_angel)
        eye_color_widget_layout.addWidget(self.eye_color_demon)
        eye_color_widget_layout.addStretch()

        eye_color_layout.addWidget(eye_color_widget)

        eye_hint = QLabel("💡 切换不同的眼睛外观风格")
        eye_hint.setProperty("class", "hint")
        eye_color_layout.addWidget(eye_hint)

        eye_color_group.setLayout(eye_color_layout)
        scroll_layout.addWidget(eye_color_group)

        # 4. 启动设置
        startup_group = QGroupBox("🚀 启动设置")
        startup_layout = QVBoxLayout()
        startup_layout.setSpacing(12)
        startup_layout.setContentsMargins(15, 20, 15, 15)

        self.auto_start_check = QCheckBox("开机自动启动")
        self.auto_start_check.setToolTip("将程序添加到 Windows 系统启动项")
        startup_layout.addWidget(self.auto_start_check)

        startup_hint = QLabel("⚠️ 需要管理员权限才能设置开机启动")
        startup_hint.setProperty("class", "hint")
        startup_layout.addWidget(startup_hint)

        startup_group.setLayout(startup_layout)
        scroll_layout.addWidget(startup_group)

        # 5. 关于
        about_group = QGroupBox("ℹ️ 关于")
        about_layout = QVBoxLayout()
        about_layout.setSpacing(6)
        about_layout.setContentsMargins(15, 20, 15, 15)

        about_text = QLabel(
            '浮空之眼 v1.0 '
            '关注 <a href="https://github.com/your-username/your-repo" style="color: #ff6b6b; text-decoration: none;">GitHub</a>'
        )
        about_text.setStyleSheet("color: #888888; font-size: 12px; line-height: 1.8; font-weight: normal;")
        about_layout.addWidget(about_text)

        about_group.setLayout(about_layout)
        scroll_layout.addWidget(about_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # 底部按钮
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 15, 0, 0)
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        reset_btn = QPushButton("↺ 恢复默认")
        reset_btn.setProperty("class", "btn-danger")
        reset_btn.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("✓ 保存设置")
        save_btn.setProperty("class", "btn-primary")
        save_btn.clicked.connect(self.save_and_apply)
        btn_layout.addWidget(save_btn)

        main_layout.addWidget(btn_widget)
        self.setLayout(main_layout)

    def load_settings(self):
        """加载设置"""
        settings = self.settings_manager.get_all_settings()

        self.use_camera_check.setChecked(settings.get('use_camera', 'true') == 'true')
        self.use_screenshot_check.setChecked(settings.get('use_screenshot', 'true') == 'true')
        self.interval_spin.setValue(int(settings.get('capture_interval', '3')))
        self.auto_start_check.setChecked(settings.get('auto_start', 'false') == 'true')

        # 加载界面主题
        theme = settings.get('theme', 'blood')
        self.current_theme = theme
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        # 加载眼睛颜色
        eye_color = settings.get('eye_color', 'default')
        if eye_color == 'angel':
            self.eye_color_angel.setChecked(True)
        elif eye_color == 'demon':
            self.eye_color_demon.setChecked(True)
        else:
            self.eye_color_default.setChecked(True)

        if not QT_MULTIMEDIA_AVAILABLE:
            self.use_camera_check.setEnabled(False)
            self.use_camera_check.setStyleSheet("color: #555555;")
            self.use_camera_check.setToolTip("相机模块不可用，请安装 QtMultimedia")

    def reset_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, "确认恢复默认",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.use_camera_check.setChecked(True)
            self.use_screenshot_check.setChecked(True)
            self.interval_spin.setValue(3)
            self.auto_start_check.setChecked(False)
            self.theme_combo.setCurrentIndex(self.theme_combo.findData('blood'))
            self.current_theme = 'blood'
            self.eye_color_default.setChecked(True)
            self.apply_theme()

    def save_and_apply(self):
        """保存并应用设置"""
        # 保存设置
        self.settings_manager.set_setting('use_camera', 'true' if self.use_camera_check.isChecked() else 'false')
        self.settings_manager.set_setting('use_screenshot', 'true' if self.use_screenshot_check.isChecked() else 'false')
        self.settings_manager.set_setting('capture_interval', str(self.interval_spin.value()))
        self.settings_manager.set_setting('auto_start', 'true' if self.auto_start_check.isChecked() else 'false')

        # 保存界面主题
        theme_key = self.theme_combo.currentData()
        self.settings_manager.set_setting('theme', theme_key)
        self.current_theme = theme_key

        # 保存眼睛颜色
        if self.eye_color_angel.isChecked():
            selected_eye = 'angel'
        elif self.eye_color_demon.isChecked():
            selected_eye = 'demon'
        else:
            selected_eye = 'default'
        self.settings_manager.set_setting('eye_color', selected_eye)

        # 应用设置到父窗口
        if self.parent:
            self.parent.apply_settings()

        QMessageBox.information(self, "✅ 设置已保存", "设置已成功保存并应用！")
        self.accept()

    def get_theme(self):
        """获取当前主题"""
        return self.current_theme


class LogDialog(QDialog):
    """历史记录弹窗"""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_page = 1
        self.page_size = 20
        self.date_filter = None
        self.total_pages = 1
        self.current_logs = []

        # 获取当前主题
        self.theme = 'blood'
        if parent and hasattr(parent, 'settings_manager'):
            self.theme = parent.settings_manager.get_setting('theme', 'blood')
        elif parent and hasattr(parent, 'current_theme'):
            self.theme = parent.current_theme

        self.setWindowTitle("👁 活动历史记录")
        self.resize(700, 500)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.center() - self.rect().center())

        self.init_ui()
        self.apply_theme()

    def apply_theme(self):
        """应用主题样式"""
        style = ThemeStyleGenerator.get_log_dialog_style(self.theme)
        self.setStyleSheet(style)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        colors = ThemeManager.get_colors(self.theme)

        title_label = QLabel("👁 活动历史记录")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {colors['title']};")
        main_layout.addWidget(title_label)

        # 筛选栏
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("📅 日期:"))

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedWidth(120)
        self.date_edit.dateChanged.connect(self.on_date_changed)
        filter_layout.addWidget(self.date_edit)

        self.quick_date_combo = QComboBox()
        self.quick_date_combo.addItems(["今天", "昨天", "最近3天", "最近7天", "全部"])
        self.quick_date_combo.setFixedWidth(100)
        self.quick_date_combo.currentTextChanged.connect(self.on_quick_date_changed)
        filter_layout.addWidget(self.quick_date_combo)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_logs)
        filter_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("✖ 清除筛选")
        clear_btn.clicked.connect(self.clear_filter)
        filter_layout.addWidget(clear_btn)

        filter_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.stats_label = QLabel("共 0 条记录")
        self.stats_label.setStyleSheet(f"font-size: 12px; font-weight: normal; color: {colors['text_muted']};")
        filter_layout.addWidget(self.stats_label)

        main_layout.addLayout(filter_layout)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {colors['separator']};")
        main_layout.addWidget(line)

        info_label = QLabel("💡 双击带有 📷 标记的记录查看截图")
        info_label.setStyleSheet(f"color: {colors['text_muted']}; font-size: 11px;")
        main_layout.addWidget(info_label)

        # 日志列表
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_click)
        main_layout.addWidget(self.list_widget)

        # 分页控制
        page_layout = QHBoxLayout()
        page_layout.setSpacing(10)

        self.prev_btn = QPushButton("◀ 上一页")
        self.prev_btn.clicked.connect(self.prev_page)
        page_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("第 1 / 1 页")
        self.page_label.setStyleSheet(f"font-size: 13px; min-width: 100px; font-weight: normal; color: {colors['text_primary']};")
        page_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("下一页 ▶")
        self.next_btn.clicked.connect(self.next_page)
        page_layout.addWidget(self.next_btn)

        page_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        page_layout.addWidget(QLabel("每页:"))

        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.setFixedWidth(60)
        self.page_size_combo.currentTextChanged.connect(self.on_page_size_changed)
        page_layout.addWidget(self.page_size_combo)

        main_layout.addLayout(page_layout)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(f"""
        QPushButton {{ border-color: {colors['border']}; }}
        QPushButton:hover {{ background-color: {colors['bg_hover']}; }}
        """)

        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.load_logs()

    def on_date_changed(self, date):
        self.date_filter = date.toString("yyyy-MM-dd")
        self.current_page = 1
        self.load_logs()

    def on_quick_date_changed(self, text):
        today = QDate.currentDate()

        if text == "今天":
            self.date_edit.setDate(today)
        elif text == "昨天":
            self.date_edit.setDate(today.addDays(-1))
        elif text == "最近3天":
            self.date_edit.setDate(today.addDays(-2))
        elif text == "最近7天":
            self.date_edit.setDate(today.addDays(-6))
        elif text == "全部":
            self.date_filter = None
            self.current_page = 1
            self.load_logs()
            return

        self.date_filter = self.date_edit.date().toString("yyyy-MM-dd")
        self.current_page = 1
        self.load_logs()

    def clear_filter(self):
        self.date_filter = None
        self.date_edit.setDate(QDate.currentDate())
        self.quick_date_combo.setCurrentText("全部")
        self.current_page = 1
        self.load_logs()

    def on_page_size_changed(self, text):
        self.page_size = int(text)
        self.current_page = 1
        self.load_logs()

    def load_logs(self):
        total_count = self.db_manager.get_total_count(self.date_filter)

        if total_count == 0:
            self.list_widget.clear()
            self.list_widget.addItem("📭 暂无记录")
            self.stats_label.setText("共 0 条记录")
            self.page_label.setText("第 0 / 0 页")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.current_logs = []
            return

        self.total_pages = (total_count + self.page_size - 1) // self.page_size

        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        rows = self.db_manager.get_logs(self.current_page, self.page_size, self.date_filter)
        self.current_logs = rows

        self.list_widget.clear()
        colors = ThemeManager.get_colors(self.theme)

        if rows:
            for row in rows:
                log_id, ts, act, screenshot = row
                time_str = ts[11:16]
                date_str = ts[:10]
                has_screenshot = screenshot is not None and len(screenshot) > 100
                icon = "📷 " if has_screenshot else " "

                if len(act) > 50:
                    act = act[:47] + "..."

                item_text = f"{icon}[{date_str} {time_str}] {act}"
                item = self.list_widget.addItem(item_text)
                self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, log_id)

                if has_screenshot:
                    text_color = colors['text_primary']
                    self.list_widget.item(self.list_widget.count() - 1).setForeground(QColor(text_color))
        else:
            self.list_widget.addItem("📭 当前页无数据")

        date_info = f" ({self.date_filter})" if self.date_filter else ""
        self.stats_label.setText(f"共 {total_count} 条记录{date_info}")
        self.page_label.setText(f"第 {self.current_page} / {self.total_pages} 页")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    def on_item_double_click(self, item):
        log_id = item.data(Qt.UserRole)
        if not log_id:
            return

        log_data = self.db_manager.get_log_by_id(log_id)
        if not log_data:
            QMessageBox.warning(self, "错误", "无法获取记录数据")
            return

        screenshot = log_data.get('screenshot')
        if not screenshot or len(screenshot) < 100:
            QMessageBox.information(self, "提示", "该记录没有截图")
            return

        pixmap = ScreenshotManager.base64_to_pixmap(screenshot)
        if pixmap and not pixmap.isNull():
            title = f"{log_data['timestamp'][:16]} - {log_data['activity'][:30]}"
            dialog = ImageViewDialog(pixmap, title, self, self.theme)
            dialog.exec()
        else:
            QMessageBox.warning(self, "错误", "无法加载截图")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_logs()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_logs()
