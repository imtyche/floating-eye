import os
import pkgutil
import importlib
import inspect
from plugins.base import BasePlugin


class PluginManager:
    _instance = None

    def __init__(self, settings_manager, parent=None):
        self.settings_manager = settings_manager
        self.parent = parent
        self.plugins = {}

        # 🌟 自动扫描并注册 plugins 目录下的所有插件
        self.discover_and_register_plugins()

    def register(self, plugin):
        """注册插件到管理器"""
        self.plugins[plugin.plugin_id] = plugin

    def discover_and_register_plugins(self):
        """🔍 动态扫描 plugins 目录"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))

            for _, module_name, is_pkg in pkgutil.iter_modules([current_dir]):
                if module_name == 'base' or module_name == 'manage' or is_pkg:
                    continue

                try:
                    module = importlib.import_module(f"plugins.{module_name}")

                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                            if obj.__module__ == module.__name__:
                                plugin_instance = obj(self.settings_manager, self.parent)
                                self.register(plugin_instance)
                                print(f"✅ 成功自动加载插件: {plugin_instance.name} (ID: {plugin_instance.plugin_id})")
                except Exception as e:
                    print(f"⚠️ 加载插件模块 '{module_name}' 失败: {e}")
        except Exception as e:
            print(f"⚠️ 自动扫描插件失败: {e}")

    def load_all_plugins(self):
        """根据持久化配置初始化已启用的插件"""
        for plugin_id, plugin in self.plugins.items():
            enabled = self.settings_manager.get_setting(f"plugin_{plugin_id}_enabled", "false") == "true"
            if enabled:
                plugin.enable()
            else:
                plugin.disable()

    def inject_settings_ui(self, target_layout, parent_widget=None):
        """🌟 自动化 UI 注入点：自动将插件配置挂载到设置对话框"""
        for plugin in self.plugins.values():
            widget = plugin.create_settings_widget(parent_widget)
            if widget:
                target_layout.addWidget(widget)