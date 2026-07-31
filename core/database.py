import pymysql
from datetime import datetime, date

class DatabaseManager:
    """数据库管理类 - 负责活动日志的存储和查询 (MySQL 版本)"""

    def __init__(self, db_config):
        """
        :param db_config: 包含 host, port, user, password, database 的字典
        """
        self.db_config = db_config
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            **self.db_config,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor
        )

    def init_db(self):
        """初始化数据库表和索引"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 创建日志表（截图数据使用 LONGBLOB）
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS logs (
                                                                   id INT AUTO_INCREMENT PRIMARY KEY,
                                                                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                                                   activity TEXT,
                                                                   screenshot LONGBLOB
                               ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                               ''')

                # 检查索引是否存在，不存在则创建
                cursor.execute("""
                               SELECT COUNT(1) AS cnt
                               FROM INFORMATION_SCHEMA.STATISTICS
                               WHERE table_schema = DATABASE()
                                 AND table_name = 'logs'
                                 AND index_name = 'idx_logs_timestamp';
                               """)
                if cursor.fetchone()['cnt'] == 0:
                    cursor.execute('''
                                   CREATE INDEX idx_logs_timestamp ON logs (timestamp DESC);
                                   ''')

            conn.commit()
        finally:
            conn.close()

    def add_log(self, activity, screenshot=None, retention_days=None):
        """添加活动日志"""
        if str(retention_days) == "-1":
            return

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO logs (timestamp, activity, screenshot) VALUES (NOW(), %s, %s)",
                    (activity, screenshot)
                )
            conn.commit()
        finally:
            conn.close()

    def get_logs(self, page=1, page_size=20, date_filter=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 强转为 int，确保不是字符串
                page = int(page)
                page_size = int(page_size)
                offset = (page - 1) * page_size

                query = "SELECT id, timestamp, activity, screenshot FROM logs"
                params = []

                if date_filter:
                    query += " WHERE DATE(timestamp) = %s"
                    params.append(str(date_filter))

                query += " ORDER BY id DESC LIMIT %s OFFSET %s"
                # 重点：此处 page_size 和 offset 必须是 int 类型！
                params.extend([page_size, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()
                # 调试点：看看查到了多少条数据
                print(f"[DEBUG] 日期过滤: {date_filter}, 查询结果条数: {len(rows)}")
                return rows
        finally:
            conn.close()

    def get_total_count(self, date_filter=None):
        """获取总记录数"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                query = "SELECT COUNT(*) AS total FROM logs"
                params = []

                if date_filter:
                    query += " WHERE DATE(timestamp) = %s"
                    params.append(date_filter)

                cursor.execute(query, params)
                result = cursor.fetchone()
                return result['total'] if result else 0
        finally:
            conn.close()

    def get_log_by_id(self, log_id):
        """根据ID获取单条日志"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, timestamp, activity, screenshot FROM logs WHERE id = %s",
                    (log_id,)
                )
                row = cursor.fetchone()
                if row and row['timestamp']:
                    row['timestamp'] = row['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                return row
        finally:
            conn.close()

    def clean_expired_logs(self, retention_days):
        """根据数据保留天数自动删除过期数据"""
        try:
            days = int(retention_days)
            if days <= 0:
                return  # 0 或负数表示不清理 (永久保存)

            conn = self.get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM logs WHERE timestamp < DATE_SUB(NOW(), INTERVAL %s DAY)",
                        (days,)
                    )
                    cleaned_count = cursor.rowcount
                conn.commit()

                if cleaned_count > 0:
                    print(f"🧹 已自动清理 {cleaned_count} 条超过 {days} 天的历史日志")
            finally:
                conn.close()
        except Exception as e:
            print(f"⚠️ 清理过期数据时出错: {e}")