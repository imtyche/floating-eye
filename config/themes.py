class ThemeManager:
    """主题管理器 - 支持三种主题"""

    THEMES = {
        'dark': {
            'name': '🌙 暗色',
            'colors': {
                'bg_primary': '#0a0a0a',
                'bg_secondary': '#141414',
                'bg_input': '#1a1a1a',
                'bg_hover': '#222222',
                'border': '#333333',
                'border_hover': '#555555',
                'border_focus': '#777777',
                'text_primary': '#cccccc',
                'text_secondary': '#999999',
                'text_muted': '#666666',
                'accent': '#666666',
                'accent_hover': '#888888',
                'accent_dark': '#222222',
                'highlight': 'rgba(136, 136, 136, 0.2)',
                'danger': '#1a1a1a',
                'danger_text': '#888888',
                'title': '#aaaaaa',
                'separator': '#1a1a1a',
                'scrollbar': '#555555',
                'scrollbar_hover': '#777777',
                'shadow': 'rgba(0, 0, 0, 0.3)',
            }
        },
        'light': {
            'name': '☀️ 亮色',
            'colors': {
                'bg_primary': '#f0ece8',
                'bg_secondary': '#e8e4e0',
                'bg_input': '#f5f2ee',
                'bg_hover': '#ddd8d0',
                'border': '#c8c0b8',
                'border_hover': '#b0a8a0',
                'border_focus': '#989088',
                'text_primary': '#3a3a3a',
                'text_secondary': '#555555',
                'text_muted': '#888888',
                'accent': '#8a7a6a',
                'accent_hover': '#a08a78',
                'accent_dark': '#5a4a3a',
                'highlight': 'rgba(138, 122, 106, 0.2)',
                'danger': '#4a2a2a',
                'danger_text': '#aa5a5a',
                'title': '#6a5a4a',
                'separator': '#d0c8c0',
                'scrollbar': '#b0a098',
                'scrollbar_hover': '#c0b0a8',
                'shadow': 'rgba(0, 0, 0, 0.06)',
            }
        },
        'blood': {
            'name': '🩸 血色',
            'colors': {
                'bg_primary': '#0a0000',
                'bg_secondary': '#140000',
                'bg_input': '#1a0005',
                'bg_hover': '#2a0008',
                'border': '#4a0a0a',
                'border_hover': '#6a1515',
                'border_focus': '#8a2020',
                'text_primary': '#e04040',
                'text_secondary': '#b03030',
                'text_muted': '#6a2020',
                'accent': '#cc2244',
                'accent_hover': '#ee3355',
                'accent_dark': '#330000',
                'highlight': 'rgba(204, 34, 68, 0.25)',
                'danger': '#2a0000',
                'danger_text': '#8a4040',
                'title': '#ff2244',
                'separator': '#2a0008',
                'scrollbar': '#cc2244',
                'scrollbar_hover': '#ee3355',
                'shadow': 'rgba(204, 34, 68, 0.08)',
            }
        }
    }

    @classmethod
    def get_theme_names(cls):
        """获取所有主题名称"""
        return {key: cls.THEMES[key]['name'] for key in cls.THEMES}

    @classmethod
    def get_colors(cls, theme_key):
        """获取主题颜色"""
        if theme_key in cls.THEMES:
            return cls.THEMES[theme_key]['colors']
        return cls.THEMES['dark']['colors']

    @classmethod
    def get_theme_name(cls, theme_key):
        """获取主题显示名称"""
        if theme_key in cls.THEMES:
            return cls.THEMES[theme_key]['name']
        return cls.THEMES['dark']['name']
