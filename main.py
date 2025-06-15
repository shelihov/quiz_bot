# Добавляем нужные импорты
import logging
import asyncio
import random
import os
from datetime import datetime
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from openai import OpenAI

# Инициализация
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

bot = Bot(token=API_TOKEN)
router = Router()
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
user_quiz_count = defaultdict(int)
user_state = {}

# Проверка доступа
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

# Команды администратора
@router.message(Command("add_user"))
async def add_user(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Нет прав.")
    args = message.text.split()
    if len(args) != 3:
        return await message.answer("/add_user <user_id> <YYYY-MM-DD>")
    uid, exp = args[1], args[2]
    with open("paid_users.txt", "a") as f:
        f.write(f"{uid}:{exp}\n")
    logger.info(f"Добавлен пользователь {uid} до {exp}")
    await message.answer(f"Пользователь {uid} добавлен до {exp}")

@router.message(Command("remove_user"))
async def remove_user(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Нет прав.")
    uid = message.text.split()[1]
    with open("paid_users.txt", "r") as f:
        lines = f.readlines()
    with open("paid_users.txt", "w") as f:
        for line in lines:
            if not line.startswith(uid + ":"):
                f.write(line)
    logger.info(f"Удалён пользователь {uid}")
    await message.answer(f"Пользователь {uid} удалён")

@router.message(Command("users"))
async def list_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        with open("paid_users.txt") as f:
            lines = f.readlines()
        text = "<b>Пользователи:</b>\n"
        for line in lines:
            uid, exp = line.strip().split(":")
            text += f"ID: <code>{uid}</code> до {exp}\n"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка при выводе пользователей: {e}")
        await message.answer("Нет пользователей")

# Команда профиля
@router.message(Command("profile"))
async def profile(message: Message):
    uid = message.from_user.id
    access = "✅ Есть" if is_paid_user(uid) else "❌ Нет"
    count = user_quiz_count.get(uid, 0)
    await message.answer(f"<b>Профиль</b>\n\nID: <code>{uid}</code>\nДоступ: {access}\nТестов создано: {count}", parse_mode="HTML")

# Команда помощи
@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📖 <b>Помощь по боту</b>\n\n"
        "Команды:\n"
        "/start — начать работу\n"
        "/profile — ваш профиль\n"
        "/generate — ввести тему вручную\n"
        "/help — справка\n"
        "\n"
        "Админ-команды:\n"
        "/add_user <id> <YYYY-MM-DD> — добавить подписчика\n"
        "/remove_user <id> — удалить подписчика\n"
        "/users — список пользователей",
        parse_mode="HTML"
    )

# Команда /generate — самостоятельный выбор темы
@router.message(Command("generate"))
async def manual_generate(message: Message):
    if not is_paid_user(message.from_user.id):
        return await message.answer("Доступ только по подписке.")
    logger.info(f"Пользователь {message.from_user.id} выбрал ручной ввод темы")
    await message.answer("Введите тему и сложность, например:\n<b>История России (Средний)</b>", parse_mode="HTML")
    user_state[message.from_user.id] = {"awaiting_prompt": True}

# Старт и квиз
@router.message(Command("start"))
async def start(message: Message):
    if not is_paid_user(message.from_user.id):
        return await message.answer("Доступ только по подписке. Напишите @shel_tg")

    keyboard = InlineKeyboardBuilder()
    subjects = ["Русский язык", "Математика", "Информатика", "Python", "Английский язык"]
    for subj in subjects:
        keyboard.button(text=subj, callback_data=f"subject:{subj}")
    keyboard.adjust(2)
    await message.answer("Выберите предмет или нажмите /generate для самостоятельного ввода темы:", reply_markup=keyboard.as_markup())

@router.callback_query(lambda c: c.data == "manual")
async def choose_manual(callback: types.CallbackQuery):
    await manual_generate(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("subject:"))
async def handle_subject(callback: types.CallbackQuery):
    subject = callback.data.split(":")[1]
    user_state[callback.from_user.id] = {"subject": subject}

    keyboard = InlineKeyboardBuilder()
    for lvl in ["Лёгкий", "Средний", "Сложный"]:
        keyboard.button(text=lvl, callback_data=f"level:{lvl}")
    await callback.message.edit_text(f"Предмет: {subject}\nВыберите уровень сложности:", reply_markup=keyboard.as_markup())
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("level:"))
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

@router.message()
async def handle_custom_prompt(message: Message):
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

async def generate_quiz(message: types.Message, prompt: str, uid: int):
    try:
        logger.info(f"Генерация теста для пользователя {uid} по теме: {prompt}")
        formatted_prompt = (
            f"{prompt}\n\n"
            "Генерируй тест-викторину по запросу строго в таком формате:\n"
        "1. Ровно 5 вопросов.\n"
        "2. После каждого блока вопроса - пустая строка.\n"
        "3. После вопроса - 4 варианта ответа (каждый с новой строки).\n"
        "4. Правильный ответ всегда первый.\n"
        "5. Никаких пояснений, только вопросы и ответы.\n"
        "6. Максимум 100 символов в строке (вопросы и ответы).\n"
        "7. Вопросы и ответы должны быть осмысленными и логичными.\n"
        "8. Сохраняй формат для Telegram-опроса.\n\n"
        "Пример:\n"
        "Что такое бессоюзное сложное предложение?\n"
        "Части связаны интонацией, без союзов.\n"
        "Предложение с союзами между частями.\n"
        "Простое предложение с однородными членами.\n"
        "Предложение с придаточными частями.\n"
        "\n"
        "Какое предложение использует правильную пунктуацию?\n"
        "Солнце село, лес затих, звезды зажглись.\n"
        "Солнце село лес затих звезды зажглись.\n"
        "Солнце село: лес затих звезды зажглись.\n"
        "Солнце село лес затих, звезды зажглись.\n"
        "\n"
        "(и ещё 3 вопроса в том же формате).\n\n"
        "Строго без лишних слов, только чистая структура."
        )
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[{"role": "user", "content": formatted_prompt}]
        )
        text = response.choices[0].message.content
        quizzes = process_quiz(text)
        if not quizzes:
            logger.warning(f"Ошибка генерации теста для пользователя {uid}: пустой результат")
            await message.answer("Ошибка генерации. Попробуйте снова.")
            return

        for quiz in quizzes:
            await bot.send_poll(
                chat_id=message.chat.id,
                question=quiz['question'],
                options=quiz['answers'],
                correct_option_id=quiz['correct_option_id'],
                type="quiz",
                is_anonymous=False
            )
        user_quiz_count[uid] += 1
        logger.info(f"Тест успешно сгенерирован и отправлен пользователю {uid}")

        # Повторный выбор
        keyboard = InlineKeyboardBuilder()
        subjects = ["Русский язык", "Математика", "Информатика", "Python", "Английский язык"]
        for subj in subjects:
            keyboard.button(text=subj, callback_data=f"subject:{subj}")
        keyboard.button(text="Выбрать тему самостоятельно", callback_data="manual")
        await message.answer("Хотите ещё? Выберите новый предмет или нажмите /generate:", reply_markup=keyboard.as_markup())
    except Exception as e:
        logger.error(f"Ошибка при генерации теста для пользователя {uid}: {e}")
        await message.answer(f"Ошибка при генерации: {e}")

def process_quiz(text: str):
    blocks = text.strip().split("\n\n")
    quizzes = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) != 5:
            continue
        question, correct, *others = lines
        options = [correct] + others
        random.shuffle(options)
        try:
            correct_id = options.index(correct)
        except ValueError:
            continue
        quizzes.append({
            "question": question,
            "answers": options,
            "correct_option_id": correct_id
        })
    return quizzes

# Запуск
async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="generate", description="Выбрать тему вручную"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="add_user", description="(Админ) Добавить пользователя"),
        BotCommand(command="remove_user", description="(Админ) Удалить пользователя"),
        BotCommand(command="users", description="(Админ) Список пользователей")
    ])
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
