# config/__init__.py
def get_theme_manager():
    from .themes import ThemeManager
    return ThemeManager

__all__ = ['get_theme_manager']
