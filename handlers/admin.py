from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_ID
from utils.logger import logger
from utils.db import add_user, remove_user, get_all_users

admin_router = Router()

@admin_router.message(Command("add_user"))
async def add_user_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Нет прав.")
    args = message.text.split()
    if len(args) != 3:
        return await message.answer("/add_user <user_id> <YYYY-MM-DD>")
    uid, exp = args[1], args[2]
    try:
        add_user(int(uid), exp)
        await message.answer(f"Пользователь {uid} добавлен до {exp}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        await message.answer("Ошибка при добавлении пользователя")

@admin_router.message(Command("remove_user"))
async def remove_user_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Нет прав.")
    uid = message.text.split()[1]
    try:
        remove_user(int(uid))
        await message.answer(f"Пользователь {uid} удалён")
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        await message.answer("Ошибка при удалении пользователя")

@admin_router.message(Command("users"))
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        users = get_all_users()
        if not users:
            return await message.answer("Нет пользователей")
        text = "<b>Пользователи:</b>\n"
        for uid, exp in users:
            text += f"ID: <code>{uid}</code> до {exp}\n"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при выводе пользователей: {e}")
        await message.answer("Ошибка при выводе пользователей")