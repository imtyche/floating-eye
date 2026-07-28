from config.themes import ThemeManager


class ThemeStyleGenerator:
    """主题样式生成器 - 为UI组件生成动态样式"""

    @staticmethod
    def get_dialog_style(theme_key):
        """生成对话框样式"""
        colors = ThemeManager.get_colors(theme_key)
        return f"""
        QDialog {{
            background-color: {colors['bg_primary']};
            border: 2px solid {colors['border']};
            border-radius: 12px;
        }}
        QLabel {{
            color: {colors['text_primary']};
            font-size: 13px;
        }}
        QLabel.title-label {{
            color: {colors['title']};
            font-size: 20px;
            font-weight: bold;
            padding: 5px 0;
        }}
        QLabel.section-title {{
            color: {colors['title']};
            font-size: 14px;
            font-weight: bold;
            padding: 8px 0 4px 0;
            border-bottom: 1px solid {colors['separator']};
        }}
        QLabel.hint {{
            color: {colors['text_muted']};
            font-size: 11px;
            font-weight: normal;
            padding-left: 28px;
        }}
        QCheckBox {{
            color: {colors['text_primary']};
            font-size: 13px;
            spacing: 10px;
            padding: 4px 0;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            background-color: {colors['bg_input']};
            border: 2px solid {colors['border']};
            border-radius: 4px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['accent']};
            border-color: {colors['accent']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors['border_hover']};
        }}
        QSpinBox {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 13px;
            min-width: 70px;
            min-height: 20px;
        }}
        QSpinBox:hover {{
            border-color: {colors['border_hover']};
        }}
        QSpinBox:focus {{
            border-color: {colors['border_focus']};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {colors['bg_secondary']};
            border: none;
            width: 20px;
            border-radius: 0;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {colors['accent']};
        }}
        QPushButton {{
            background-color: {colors['bg_secondary']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: bold;
            font-size: 13px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {colors['bg_hover']};
            border-color: {colors['border_hover']};
        }}
        QPushButton.btn-primary {{
            background-color: {colors['accent']};
            border-color: {colors['accent']};
            color: white;
        }}
        QPushButton.btn-primary:hover {{
            background-color: {colors['accent_hover']};
            border-color: {colors['accent_hover']};
        }}
        QPushButton.btn-danger {{
            background-color: {colors['danger']};
            border-color: {colors['border']};
            color: {colors['danger_text']};
        }}
        QPushButton.btn-danger:hover {{
            background-color: {colors['bg_hover']};
            border-color: {colors['border_hover']};
        }}
        QFrame.separator {{
            background-color: {colors['separator']};
            border: none;
            max-height: 2px;
        }}
        QGroupBox {{
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 15px;
            padding: 0 10px;
            color: {colors['title']};
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: {colors['bg_secondary']};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {colors['scrollbar']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors['scrollbar_hover']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QComboBox {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 13px;
            min-width: 100px;
        }}
        QComboBox:hover {{
            border-color: {colors['border_hover']};
        }}
        QComboBox:focus {{
            border-color: {colors['border_focus']};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_primary']};
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            selection-background-color: {colors['highlight']};
            selection-color: {colors['text_primary']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 5px 10px;
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {colors['bg_hover']};
            color: {colors['text_primary']};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {colors['highlight']};
            color: {colors['text_primary']};
        }}
        """

    @staticmethod
    def get_list_widget_style(theme_key):
        """生成列表样式"""
        colors = ThemeManager.get_colors(theme_key)
        return f"""
        QListWidget {{
            background: {colors['bg_secondary']};
            color: {colors['text_secondary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            font-size: 12px;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {colors['separator']};
            color: {colors['text_secondary']};
        }}
        QListWidget::item:selected {{
            background: {colors['highlight']};
            color: {colors['text_primary']};
        }}
        QListWidget::item:hover {{
            background: {colors['bg_hover']};
        }}
        """

    @staticmethod
    def get_log_dialog_style(theme_key):
        """生成历史记录对话框样式"""
        colors = ThemeManager.get_colors(theme_key)
        list_style = ThemeStyleGenerator.get_list_widget_style(theme_key)
        return f"""
        QDialog {{
            background-color: {colors['bg_primary']};
            border: 2px solid {colors['border']};
            border-radius: 8px;
        }}
        QLabel {{
            color: {colors['text_primary']};
            font-weight: bold;
            font-size: 13px;
        }}
        QLabel[text=""] {{
            color: {colors['text_muted']};
        }}
        QComboBox {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            border-color: {colors['border_hover']};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_primary']};
            margin-right: 4px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            selection-background-color: {colors['highlight']};
            selection-color: {colors['text_primary']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 4px 8px;
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {colors['bg_hover']};
            color: {colors['text_primary']};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {colors['highlight']};
            color: {colors['text_primary']};
        }}
        QDateEdit {{
            background-color: {colors['bg_input']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }}
        QDateEdit:hover {{
            border-color: {colors['border_hover']};
        }}
        QDateEdit::drop-down {{
            border: none;
            background: transparent;
        }}
        QDateEdit::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_primary']};
            margin-right: 4px;
        }}
        QCalendarWidget QAbstractItemView {{
            background-color: {colors['bg_primary']};
            color: {colors['text_primary']};
        }}
        QCalendarWidget QAbstractItemView::item {{
            color: {colors['text_primary']};
        }}
        QCalendarWidget QAbstractItemView::item:selected {{
            background-color: {colors['highlight']};
            color: {colors['text_primary']};
        }}
        {list_style}
        QPushButton {{
            background-color: {colors['bg_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: {colors['bg_hover']};
            border-color: {colors['border_hover']};
        }}
        QPushButton:disabled {{
            background-color: {colors['bg_primary']};
            color: {colors['text_muted']};
            border-color: {colors['separator']};
        }}
        QFrame {{
            background-color: {colors['separator']};
        }}
        """
