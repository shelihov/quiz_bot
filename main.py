import logging
import asyncio
import random
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv
from openai import OpenAI

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')  # Telegram Bot Token
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')  # OpenRouter API Key

if not API_TOKEN:
    raise ValueError("Токен бота не найден. Убедитесь, что переменная окружения BOT_TOKEN установлена.")
if not OPENROUTER_API_KEY:
    raise ValueError("Ключ API OpenRouter не найден. Убедитесь, что переменная окружения OPENROUTER_API_KEY установлена.")

# Initialize bot, router, and OpenAI client
bot = Bot(token=API_TOKEN)
router = Router()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Глобальная переменная для хранения последнего промпта
last_prompt = None

# Handler for /start command
@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Введите запрос для генерации тестов (например, 'английский язык: Past Simple'):")

@router.message()
async def handle_prompt(message: types.Message):
    global last_prompt
    last_prompt = message.text  # Сохраняем последний промпт
    await generate_quiz(message, last_prompt)

async def generate_quiz(message: types.Message, prompt: str):
    # Формируем запрос для модели
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
    await message.reply("Генерирую тесты, подождите...")

    try:
        # Логируем отправку запроса
        logger.info("Отправка запроса к OpenRouter API с prompt: %s", formatted_prompt)

        # Отправляем запрос к OpenRouter API
        completion = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ]
        )
        response = completion.choices[0].message.content

        # Логируем полученный ответ
        logger.info("Получен ответ от OpenRouter API: %s", response)
        if not response.strip():
            await send_retry_button(message, "Не удалось сгенерировать тесты. Попробуйте другой запрос.")
            return

        # Обрабатываем ответ и генерируем тесты
        quizzes = process_generated_quizzes(response)
        if not quizzes:
            await send_retry_button(message, "Не удалось обработать тесты. Попробуйте другой запрос.")
            return

        for quiz in quizzes:
            await bot.send_poll(
                chat_id=message.chat.id,
                question=quiz['question'],
                options=quiz['answers'],
                type='quiz',
                correct_option_id=quiz['correct_option_id'],
                is_anonymous=False,
                allows_multiple_answers=False
            )
    except Exception as e:
        # Логируем ошибку
        logger.error("Ошибка при генерации тестов: %s", e)
        # Выводим сообщение об ошибке с кнопкой "Обновить"
        await send_retry_button(message, f"Ошибка при генерации тестов: {e}")

async def send_retry_button(message: types.Message, error_message: str):
    """Отправляет сообщение с кнопкой для повторной отправки запроса."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обновить", callback_data="retry")]
        ]
    )
    await message.reply(error_message, reply_markup=keyboard)

@router.callback_query()
async def handle_retry(callback_query: types.CallbackQuery):
    """Обрабатывает нажатие на кнопку "Обновить"."""
    global last_prompt
    if last_prompt:
        await generate_quiz(callback_query.message, last_prompt)
    else:
        await callback_query.message.reply("Промпт не найден. Введите запрос заново.")
    await callback_query.answer()

def process_generated_quizzes(response: str):
    """Обрабатывает ответ от API и преобразует его в формат для опросов."""
    blocks = response.strip().split('\n\n')
    quizzes = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) != 5:
            continue  # Пропускаем некорректные блоки
        question, correct_answer, *other_answers = lines
        answers = [correct_answer] + other_answers
        random.shuffle(answers)
        correct_answer_index = answers.index(correct_answer)
        quizzes.append({
            'question': question.strip(),
            'answers': [ans.strip() for ans in answers],
            'correct_option_id': correct_answer_index
        })
    return quizzes

async def main():
    # Initialize dispatcher and register router
    dp = Dispatcher()
    dp.include_router(router)

    # Start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")

if __name__ == '__main__':
    asyncio.run(main())