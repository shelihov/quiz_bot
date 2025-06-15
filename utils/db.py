import sqlite3
from datetime import datetime
from utils.logger import logger
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                exp_date TEXT NOT NULL
            )
        ''')
        conn.commit()


def add_user(user_id: int, exp_date: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('REPLACE INTO users (user_id, exp_date) VALUES (?, ?)', (user_id, exp_date))
        conn.commit()
        logger.info(f"Добавлен пользователь {user_id} до {exp_date}")


def remove_user(user_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        logger.info(f"Удалён пользователь {user_id}")


def get_all_users():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT user_id, exp_date FROM users')
        return c.fetchall()


def is_paid_user(user_id: int, admin_id: int) -> bool:
    if user_id == admin_id:
        return True
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT exp_date FROM users WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        if row:
            exp = row[0]
            logger.info(f"Проверка доступа для пользователя {user_id}: найден, exp={exp}")
            return datetime.now() < datetime.strptime(exp, "%Y-%m-%d")
    return False
