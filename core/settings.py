import sqlite3


class SettingsManager:
    """设置管理类 - 负责应用程序配置的持久化"""

    def __init__(self, db_name="activity_log.db"):
        self.db_name = db_name
        self.init_settings_table()

    def init_settings_table(self):
        """创建设置表并初始化默认值"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS settings (
                                                               key TEXT PRIMARY KEY,
                                                               value TEXT
                       )
                       ''')

        # 默认设置
        default_settings = {
            'use_camera': 'true',
            'use_screenshot': 'true',
            'capture_interval': '3',
            'auto_start': 'false',
            'theme': 'blood',
            'eye_color': 'default'
        }

        for key, value in default_settings.items():
            cursor.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

        conn.commit()
        conn.close()

    def get_setting(self, key, default=None):
        """获取单个设置值"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key, value):
        """设置单个配置值"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()
        conn.close()

    def get_all_settings(self):
        """获取所有设置"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
