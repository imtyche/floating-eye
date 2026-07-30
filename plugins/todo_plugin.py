import json
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QCheckBox, QGroupBox, QMessageBox, QWidget
)
from plugins.base import BasePlugin


class TodoDialog(QDialog):
    """待办事项主界面对话框"""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle("📝 待办事项")
        self.resize(360, 480)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 黑暗/暗红风样式表
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1d;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2b2b36;
                color: #ffffff;
                border: 1px solid #444454;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #ff4d4d;
            }
            QListWidget {
                background-color: #222226;
                border: 1px solid #33333d;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #2b2b36;
                border-radius: 4px;
                margin-bottom: 4px;
                padding: 0px;
            }
            QPushButton {
                background-color: #ff3333;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
            QPushButton#btn_delete {
                background-color: #3a3a44;
                color: #ff5555;
                border: 1px solid #4a4a58;
                border-radius: 4px;
                font-size: 11px;
                font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
                padding: 3px 6px;
                text-align: center;
            }
            QPushButton#btn_delete:hover {
                background-color: #e63946;
                color: #ffffff;
                border: none;
            }
        """)

        self.init_ui()
        self.load_todos()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 顶部输入栏
        input_layout = QHBoxLayout()
        self.txt_input = QLineEdit(self)
        self.txt_input.setPlaceholderText("添加新的待办事项...")
        self.txt_input.returnPressed.connect(self.add_todo)

        btn_add = QPushButton("添加", self)
        btn_add.clicked.connect(self.add_todo)

        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(btn_add)
        layout.addLayout(input_layout)

        # 待办列表
        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self.edit_todo_item)
        layout.addWidget(self.list_widget)

    def load_todos(self):
        """加载待办列表数据"""
        self.list_widget.clear()
        todos = self.plugin.get_todos()

        for todo in todos:
            self._create_item_widget(todo["id"], todo["text"], todo["completed"])

    def _create_item_widget(self, todo_id, text, completed):
        """创建单个 ListWidgetItem 项"""
        item = QListWidgetItem(self.list_widget)
        item.setData(Qt.UserRole, todo_id)

        widget = QWidget()
        h_layout = QHBoxLayout(widget)
        h_layout.setContentsMargins(8, 4, 8, 4)
        h_layout.setSpacing(8)

        # 状态复选框
        chk = QCheckBox(text, widget)
        chk.setChecked(completed)
        chk.setStyleSheet(f"""
            QCheckBox {{
                color: {'#888888' if completed else '#ffffff'};
                text-decoration: {'line-through' if completed else 'none'};
                font-size: 13px;
            }}
        """)
        chk.toggled.connect(lambda state: self.toggle_todo(todo_id, state, chk))

        # 删除按钮
        btn_del = QPushButton("删除", widget)
        btn_del.setObjectName("btn_delete")
        btn_del.setFixedWidth(52)
        btn_del.setFixedHeight(24)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.clicked.connect(lambda: self.delete_todo(todo_id))

        h_layout.addWidget(chk, 1)
        h_layout.addWidget(btn_del, 0, Qt.AlignVCenter)

        # 强制设置整行 Height 尺寸约束，防止显示裁剪或偏斜
        item.setSizeHint(QSize(0, 38))

        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def add_todo(self):
        """添加任务"""
        text = self.txt_input.text().strip()
        if not text:
            return
        self.plugin.add_todo(text)
        self.txt_input.clear()
        self.load_todos()

    def toggle_todo(self, todo_id, completed, chk_box):
        """确认完成/取消完成"""
        self.plugin.toggle_todo(todo_id, completed)
        chk_box.setStyleSheet(f"""
            QCheckBox {{
                color: {'#888888' if completed else '#ffffff'};
                text-decoration: {'line-through' if completed else 'none'};
                font-size: 13px;
            }}
        """)

    def edit_todo_item(self, item):
        """双击修改任务文本"""
        todo_id = item.data(Qt.UserRole)
        todos = self.plugin.get_todos()
        current_todo = next((t for t in todos if t["id"] == todo_id), None)

        if not current_todo:
            return

        from PySide6.QtWidgets import QInputDialog
        new_text, ok = QInputDialog.getText(
            self, "修改待办", "更新待办事项内容:",
            QLineEdit.Normal, current_todo["text"]
        )

        if ok and new_text.strip():
            self.plugin.edit_todo(todo_id, new_text.strip())
            self.load_todos()

    def delete_todo(self, todo_id):
        """删除任务"""
        self.plugin.delete_todo(todo_id)
        self.load_todos()


class TodoPlugin(BasePlugin):
    """眼睛双击待办事项插件"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(settings_manager, parent)
        self.dialog = None

    @property
    def plugin_id(self) -> str:
        return "todo_list"

    @property
    def name(self) -> str:
        return "📋 悬浮眼睛待办事项"

    def show_todo_dialog(self):
        """唤起/显示待办窗口"""
        if not self.is_enabled:
            return

        if not self.dialog or not self.dialog.isVisible():
            self.dialog = TodoDialog(self, parent=self.parent())
            self.dialog.show()
        else:
            self.dialog.activateWindow()

    # ===== 数据持久化读写 =====
    def get_todos(self) -> list:
        raw_json = self.settings_manager.get_setting("todo_items_data", "[]")
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return []

    def _save_todos(self, todos: list):
        self.settings_manager.set_setting("todo_items_data", json.dumps(todos, ensure_ascii=False))

    def add_todo(self, text: str):
        todos = self.get_todos()
        import time
        new_item = {
            "id": int(time.time() * 1000),
            "text": text,
            "completed": False
        }
        todos.append(new_item)
        self._save_todos(todos)

    def toggle_todo(self, todo_id: int, completed: bool):
        todos = self.get_todos()
        for item in todos:
            if item["id"] == todo_id:
                item["completed"] = completed
                break
        self._save_todos(todos)

    def edit_todo(self, todo_id: int, new_text: str):
        todos = self.get_todos()
        for item in todos:
            if item["id"] == todo_id:
                item["text"] = new_text
                break
        self._save_todos(todos)

    def delete_todo(self, todo_id: int):
        todos = [t for t in self.get_todos() if t["id"] != todo_id]
        self._save_todos(todos)

    def create_settings_widget(self, parent=None) -> QWidget:
        group = QGroupBox("📋 待办事项插件", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 20, 15, 15)

        chk_enable = QCheckBox("启用双击眼睛打开待办事项列表", group)
        is_enabled = self.settings_manager.get_setting("plugin_todo_list_enabled", "false") == "true"
        chk_enable.setChecked(is_enabled)

        def on_toggle(checked):
            self.settings_manager.set_setting("plugin_todo_list_enabled", "true" if checked else "false")
            if checked:
                self.enable()
            else:
                self.disable()

        chk_enable.toggled.connect(on_toggle)
        layout.addWidget(chk_enable)
        return group