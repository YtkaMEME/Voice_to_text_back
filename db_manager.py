import sqlite3
import os

DB_PATH = "file_tracking.db"

class DBManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_files (
                    user_id INTEGER,
                    original_name TEXT,
                    transcript_name TEXT,
                    expected_files INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def add_file_record(self, user_id: int, original_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_files (user_id, original_name, transcript_name, expected_files)
                VALUES (?, ?, NULL, 1)
            """, (user_id, original_name))
            conn.commit()

    def set_transcript_name(self, user_id: int, original_name: str, transcript_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_files
                SET transcript_name = ?, expected_files = expected_files - 1
                WHERE user_id = ? AND original_name = ?
            """, (transcript_name, user_id, original_name))
            conn.commit()

    def get_pending_file(self, user_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT transcript_name FROM user_files
                WHERE user_id = ? AND transcript_name IS NOT NULL
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def delete_file_record(self, user_id: int, transcript_name: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM user_files
                WHERE user_id = ? AND transcript_name = ?
            """, (user_id, transcript_name))
            conn.commit()

    def get_expected_files_count(self, user_id: int) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(expected_files) FROM user_files
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0