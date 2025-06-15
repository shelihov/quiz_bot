from datetime import datetime
from config import ADMIN_ID
from utils.logger import logger
from utils.db import is_paid_user as db_is_paid_user

def is_paid_user(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        with open("paid_users.txt", "r") as f:
            for line in f:
                uid, exp = line.strip().split(":")
                if str(user_id) == uid:
                    logger.info(f"Проверка доступа для пользователя {user_id}: найден, exp={exp}")
                    return datetime.now() < datetime.strptime(exp, "%Y-%m-%d")
    except Exception as e:
        logger.error(f"Ошибка при проверке доступа: {e}")
    return False

def is_paid_user_wrapper(user_id: int) -> bool:
    return db_is_paid_user(user_id, ADMIN_ID)