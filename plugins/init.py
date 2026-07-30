# ✅ 修复后的 plugins/__init__.py
from .base import BasePlugin
from .translation_plugin import TranslationPlugin, TranslationWorker
from .manager import PluginManager  # 注意匹配文件名 manage.py

__all__ = [
    'BasePlugin',
    'PluginManager',
    'TranslationWorker',
    'TranslationPlugin'
]