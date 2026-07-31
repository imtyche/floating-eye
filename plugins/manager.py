import inspect
from plugins.base import BasePlugin
# 显式导入插件模块，确保打包后能稳定加载
import plugins.todo_plugin as todo_plugin
import plugins.healthy_plugin as healthy_plugin


class PluginManager:
    _instance = None

    def __init__(self, settings_manager, parent=None):
        self.settings_manager = settings_manager
        self.parent = parent
        self.plugins = {}

        # 🌟 自动扫描并注册插件
        self.discover_and_register_plugins()

    def register(self, plugin):
        """注册插件到管理器"""
        self.plugins[plugin.plugin_id] = plugin

    def discover_and_register_plugins(self):
        """🔍 注册插件模块"""
        # 如果后续增加了新插件，只需在这里将模块名加进列表即可
        plugin_modules = [
            healthy_plugin,
            todo_plugin,
        ]

        for module in plugin_modules:
            try:
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        if obj.__module__ == module.__name__:
                            plugin_instance = obj(self.settings_manager, self.parent)
                            self.register(plugin_instance)
                            print(f"✅ 成功加载插件: {plugin_instance.name} (ID: {plugin_instance.plugin_id})")
            except Exception as e:
                print(f"⚠️ 加载插件模块 '{module}' 失败: {e}")

    def load_all_plugins(self):
        """🌟 根据持久化配置初始化已启用的插件（之前丢失的方法）"""
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