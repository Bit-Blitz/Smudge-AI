import sqlite3
import json
import time
from utils.logger import logger

class DatabaseManager:
    def __init__(self, db_path="d:/Ceaser-AI/logs/aegis_history.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create execution_history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    goal TEXT,
                    plan TEXT,
                    status TEXT,
                    details TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def log_step(self, goal, plan, status, details=None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert dicts to JSON strings for storage
            plan_str = json.dumps(plan) if isinstance(plan, (dict, list)) else str(plan)
            details_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
            
            cursor.execute('''
                INSERT INTO execution_history (timestamp, goal, plan, status, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (time.time(), goal, plan_str, status, details_str))
            
            conn.commit()
            conn.close()
            # logger.debug("Step logged to database.")
        except Exception as e:
            logger.error(f"Failed to log step to database: {e}")

    def get_recent_history(self, limit=10):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM execution_history 
                ORDER BY id DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append(dict(row))
            
            return history
        except Exception as e:
            logger.error(f"Failed to fetch history: {e}")
            return []

    def clear_history(self):
        """Clears all records from the execution_history table."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM execution_history')
            conn.commit()
            conn.close()
            logger.info("Execution history cleared from database.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            return False
