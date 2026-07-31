import sqlite3
from datetime import datetime


class DatabaseManager:
    """数据库管理类 - 负责活动日志的存储和查询"""

    def __init__(self, db_name="activity_log.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """初始化数据库表和索引"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建日志表
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS logs (
                                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                           timestamp TEXT,
                                                           activity TEXT,
                                                           screenshot BLOB
                       )
                       ''')

        # 索引1：按日期查询优化
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_logs_date
                           ON logs (substr(timestamp, 1, 10))
                       ''')

        # 索引2：优化按时间倒序排列
        cursor.execute('''
                       CREATE INDEX IF NOT EXISTS idx_logs_timestamp_desc
                           ON logs (timestamp DESC)
                       ''')

        conn.commit()
        conn.close()

    def add_log(self, activity, screenshot=None, retention_days=None):
        """添加活动日志"""
        # 如果保留天数为 -1，表示永不保存，直接跳过插入
        if str(retention_days) == "-1":
            return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO logs (timestamp, activity, screenshot) VALUES (?, ?, ?)",
            (now, activity, screenshot)
        )
        conn.commit()
        conn.close()

    def get_logs(self, page=1, page_size=20, date_filter=None):
        """分页获取日志"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        offset = (page - 1) * page_size
        query = "SELECT id, timestamp, activity, screenshot FROM logs"
        params = []

        if date_filter:
            query += " WHERE DATE(timestamp) = ?"
            params.append(date_filter)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_total_count(self, date_filter=None):
        """获取总记录数"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM logs"
        params = []

        if date_filter:
            query += " WHERE DATE(timestamp) = ?"
            params.append(date_filter)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_log_by_id(self, log_id):
        """根据ID获取单条日志"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, activity, screenshot FROM logs WHERE id = ?",
            (log_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'timestamp': row[1],
                'activity': row[2],
                'screenshot': row[3]
            }
        return None
    # 清理过期数据
    def clean_expired_logs(self, retention_days):
        """根据数据保留天数自动删除过期数据"""
        try:
            days = int(retention_days)
            if days <= 0:
                return  # 0 或负数表示不清理 (永久保存)

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # 删除 timestamp 小于 N 天前的日志数据
            cursor.execute(
                "DELETE FROM logs WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days', 'localtime')",
                (days,)
            )
            cleaned_count = cursor.rowcount
            conn.commit()
            conn.close()
            if cleaned_count > 0:
                print(f"🧹 已自动清理 {cleaned_count} 条超过 {days} 天的历史日志")
        except Exception as e:
            print(f"⚠️ 清理过期数据时出错: {e}")
