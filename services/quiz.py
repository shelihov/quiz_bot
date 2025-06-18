# Вынесем генерацию теста и обработку результатов в отдельный файл

import random
from collections import defaultdict
from openai import OpenAI
from config import OPENROUTER_API_KEY
from utils.logger import logger
from bot import bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
user_quiz_count = defaultdict(int)
user_state = {}

async def generate_quiz(message, prompt, uid):
    try:
        logger.info(f"Генерация теста для пользователя {uid} по теме: {prompt}")
        start_time = datetime.now()  # время начала генерации
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
            model="google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": formatted_prompt}]
        )
        text = response.choices[0].message.content
        quizzes = process_quiz(text)
        if not quizzes:
            logger.warning(f"Ошибка генерации теста для пользователя {uid}: пустой результат")
            await message.answer("Ошибка генерации. Попробуйте снова.")
            return

        gen_time = (datetime.now() - start_time).total_seconds()
        await message.answer(
            f"✅ Тест сгенерирован за {gen_time:.1f} сек.\n"
            "Сейчас отправляю вопросы..."
        )

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
            keyboard.adjust(2)
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