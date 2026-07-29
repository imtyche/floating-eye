from abc import ABC, ABCMeta
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


class QABCMeta(type(QObject), ABCMeta):
    """解决 PySide6 ObjectType 与 Python ABCMeta 的元类冲突"""
    pass


class BasePlugin(QObject, ABC, metaclass=QABCMeta):
    """插件基类"""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.is_enabled = False

    @property
    def plugin_id(self) -> str:
        """插件唯一 ID"""
        raise NotImplementedError

    @property
    def name(self) -> str:
        """插件显示名称"""
        raise NotImplementedError

    def enable(self):
        """启用插件逻辑"""
        self.is_enabled = True

    def disable(self):
        """禁用插件逻辑"""
        self.is_enabled = False

    def create_settings_widget(self, parent=None) -> QWidget:
        """
        [可选接口] 返回该插件专属的 UI 设置控件。
        设置对话框打开时会自动调用并渲染此组件，不需要修改 settings 页面代码。
        """
        return None