import pymysql


class SettingsManager:
    """设置管理类 - 负责应用程序配置的持久化 (MySQL 版本)"""

    def __init__(self, db_config):
        """
        :param db_config: 包含 host, port, user, password, database 的字典
        """
        self.db_config = db_config
        self.init_settings_table()

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.db_config,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor
        )

    def init_settings_table(self):
        """创建设置表并初始化默认值"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS settings (
                                                                       `key` VARCHAR(100) PRIMARY KEY,
                                   `value` TEXT
                                   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                               ''')

                # 默认设置
                default_settings = {
                    'use_camera': 'true',
                    'use_screenshot': 'true',
                    'capture_interval': '3',
                    'auto_start': 'false',
                    'theme': 'blood',
                    'eye_color': 'default',
                    'retention_days': '0'
                }

                # MySQL 使用 INSERT IGNORE 忽略已存在的 key
                for key, value in default_settings.items():
                    cursor.execute(
                        "INSERT IGNORE INTO settings (`key`, `value`) VALUES (%s, %s)",
                        (key, value)
                    )
            conn.commit()
        finally:
            conn.close()

    def get_setting(self, key, default=None):
        """获取单个设置值"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT `value` FROM settings WHERE `key` = %s", (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        finally:
            conn.close()

    def set_setting(self, key, value):
        """设置单个配置值"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 使用 ON DUPLICATE KEY UPDATE 实现 REPLACE 效果
                cursor.execute(
                    """
                    INSERT INTO settings (`key`, `value`) VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)
                    """,
                    (key, value)
                )
            conn.commit()
        finally:
            conn.close()

    def get_all_settings(self):
        """获取所有设置"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT `key`, `value` FROM settings")
                rows = cursor.fetchall()
                return {row['key']: row['value'] for row in rows}
        finally:
            conn.close()