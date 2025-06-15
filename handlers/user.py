# Вынесенные пользовательские хендлеры
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.access import is_paid_user_wrapper as is_paid_user
from services.quiz import generate_quiz, user_quiz_count, user_state
from utils.logger import logger

user_router = Router()

@user_router.message(Command("profile"))
async def profile(message: types.Message):
    uid = message.from_user.id
    access = "✅ Есть" if is_paid_user(uid) else "❌ Нет"
    count = user_quiz_count.get(uid, 0)
    await message.answer(f"<b>Профиль</b>\n\nID: <code>{uid}</code>\nДоступ: {access}\nТестов создано: {count}", parse_mode="HTML")

@user_router.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 <b>Помощь по боту</b>\n\n"
        "Команды:\n"
        "/start — начать работу\n"
        "/profile — ваш профиль\n"
        "/generate — ввести тему вручную\n"
        "/help — справка\n"
        "\n"
        "Админ-команды:\n"
        "/add_user <code>id</code> <code>YYYY-MM-DD</code> — добавить подписчика\n"
        "/remove_user <code>id</code> — удалить подписчика\n"
        "/users — список пользователей",
        parse_mode="HTML"
    )

@user_router.message(Command("generate"))
async def manual_generate(message: types.Message):
    if not is_paid_user(message.from_user.id):
        return await message.answer("Доступ только по подписке.")
    logger.info(f"Пользователь {message.from_user.id} выбрал ручной ввод темы")
    await message.answer("Введите тему и сложность, например:\n<b>История России (Средний)</b>", parse_mode="HTML")
    user_state[message.from_user.id] = {"awaiting_prompt": True}

@user_router.message(Command("start"))
async def start(message: types.Message):
    if not is_paid_user(message.from_user.id):
        return await message.answer("Доступ только по подписке. Напишите @shel_tg")

    keyboard = InlineKeyboardBuilder()
    subjects = ["Русский язык", "Математика", "Информатика", "Python", "Английский язык"]
    for subj in subjects:
        keyboard.button(text=subj, callback_data=f"subject:{subj}")
    keyboard.adjust(2)
    await message.answer("Выберите предмет или нажмите /generate для самостоятельного ввода темы:", reply_markup=keyboard.as_markup())

@user_router.callback_query(lambda c: c.data == "manual")
async def choose_manual(callback: types.CallbackQuery):
    await manual_generate(callback.message)
    await callback.answer()

@user_router.callback_query(lambda c: c.data.startswith("subject:"))
async def handle_subject(callback: types.CallbackQuery):
    subject = callback.data.split(":")[1]
    user_state[callback.from_user.id] = {"subject": subject}

    keyboard = InlineKeyboardBuilder()
    for lvl in ["Лёгкий", "Средний", "Сложный"]:
        keyboard.button(text=lvl, callback_data=f"level:{lvl}")
    await callback.message.edit_text(f"Предмет: {subject}\nВыберите уровень сложности:", reply_markup=keyboard.as_markup())
    await callback.answer()

@user_router.callback_query(lambda c: c.data.startswith("level:"))
async def handle_level(callback: types.CallbackQuery):
    level = callback.data.split(":")[1]
    uid = callback.from_user.id
    state = user_state.get(uid, {})
    subject = state.get("subject")
    if not subject:
        return await callback.message.answer("Ошибка. Начните сначала: /start")
    prompt = f"{subject} ({level} уровень сложности)"
    logger.info(f"Пользователь {uid} выбрал предмет '{subject}' и уровень '{level}'")
    await callback.message.edit_text(f"Генерируем тест по теме: {prompt}...")
    asyncio.create_task(generate_quiz(callback.message, prompt, uid))
    await callback.answer()

@user_router.message()
async def handle_custom_prompt(message: types.Message):
    # Если это команда — не обрабатывать
    if message.text and message.text.startswith("/"):
        return
    uid = message.from_user.id
    # Разрешаем ввод темы только если пользователь в состоянии "awaiting_prompt"
    if user_state.get(uid, {}).get("awaiting_prompt"):
        user_state[uid]["awaiting_prompt"] = False
        prompt = message.text
        logger.info(f"Пользователь {uid} ввёл тему: {prompt}")
        await message.answer(f"Генерируем тест по теме: {prompt}...")
        asyncio.create_task(generate_quiz(message, prompt, uid))
    else:
        # Если пользователь не нажимал /generate — игнорируем или отправляем подсказку
        await message.answer("Чтобы ввести тему, сначала нажмите /generate.")