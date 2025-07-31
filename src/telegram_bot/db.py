import sqlite3
from typing import Optional, Tuple

DB_NAME = "database.db"


def init_db() -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Таблица пользователей
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                minutes_balance INTEGER DEFAULT 0,
                free_video INTEGER DEFAULT 1,
                video_balance INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0
            )
            """
        )

        # Таблица логов покупок
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS purchase_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                purchase_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now','localtime'))
            )
            """
        )

        conn.commit()


def get_user(user_id: int) -> Optional[Tuple]:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row


def create_user(user_id: int) -> None:
    if get_user(user_id) is not None:
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, minutes_balance, free_video, video_balance, banned)
            VALUES (?, 0, 1, 0, 0)
            """,
            (user_id,),
        )
        conn.commit()


def update_minutes_balance(user_id: int, new_balance: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET minutes_balance = ? WHERE user_id = ?",
            (new_balance, user_id),
        )
        conn.commit()


def update_video_balance(user_id: int, new_balance: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET video_balance = ? WHERE user_id = ?",
            (new_balance, user_id),
        )
        conn.commit()


def set_free_video(user_id: int, value: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET free_video = ? WHERE user_id = ?",
            (value, user_id),
        )
        conn.commit()


def set_banned(user_id: int, value: int) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET banned = ? WHERE user_id = ?",
            (value, user_id),
        )
        conn.commit()
