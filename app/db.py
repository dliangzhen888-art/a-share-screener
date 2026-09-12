"""基于 Python 标准库 sqlite3 的最小数据库初始化。"""

import sqlite3

from app.config import DATABASE_PATH, DATA_DIR


def initialize_database() -> None:
    """创建数据目录、数据库文件和基础元数据表。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
