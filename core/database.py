import sqlite3
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class DatabaseManager:
    """数据库管理类 - 负责活动日志的存储和查询"""

    def __init__(self, db_name="activity_log.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """初始化数据库表和索引"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 创建活动日志表
        cursor.execute('''
           CREATE TABLE IF NOT EXISTS logs (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               timestamp TEXT,
               activity TEXT,
               screenshot BLOB
           )
           ''')
        # 创建系统日志表
        cursor.execute('''
           CREATE TABLE IF NOT EXISTS crash_logs (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             timestamp TEXT,
             exc_type TEXT,
             exc_value TEXT,
             stack_trace TEXT
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
        if str(retention_days) == "-1":
            return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # 替换为带时区/本地时区的当前时间
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO logs (timestamp, activity, screenshot) VALUES (?, ?, ?)",
            (now, activity, screenshot),
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
    from datetime import datetime, timedelta

    def clean_expired_logs(self, retention_days):
        """根据数据保留天数自动删除过期数据"""
        try:
            days = int(retention_days)
            if days <= 0:
                return  # 0 或负数表示不清理 (永久保存)

            # 1. 在 Python 端算好 N 天前的本地绝对时间字符串
            cutoff_date = (datetime.now().astimezone() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # 2. 直接比较字符串（标准 ISO 格式的时间字符串可以直接比大小）
            cursor.execute(
                "DELETE FROM logs WHERE timestamp < ?",
                (cutoff_date,)
            )
            cleaned_count = cursor.rowcount
            conn.commit()
            conn.close()

            if cleaned_count > 0:
                print(f"🧹 已自动清理 {cleaned_count} 条在 {cutoff_date} 之前的历史日志")
        except Exception as e:
            print(f"⚠️ 清理过期数据时出错: {e}")

    # 新增保存闪退日志方法
    def add_crash_log(self, exc_type, exc_value, exc_tb):
        """记录崩溃/闪退日志"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

            # 格式化堆栈信息为字符串
            if isinstance(exc_tb, str):
                stack_trace = exc_tb
            else:
                stack_trace = "".join(traceback.format_tb(exc_tb))

            type_str = str(exc_type.__name__) if hasattr(exc_type, '__name__') else str(exc_type)
            value_str = str(exc_value)

            cursor.execute(
                "INSERT INTO crash_logs (timestamp, exc_type, exc_value, stack_trace) VALUES (?, ?, ?, ?)",
                (now, type_str, value_str, stack_trace)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"写入崩溃日志到数据库失败: {e}")
