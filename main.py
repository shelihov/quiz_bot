import asyncio
import random
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_TOKEN = os.getenv('BOT_TOKEN')  # Use environment variable for the bot token

if not API_TOKEN:
    raise ValueError("Токен бота не найден. Убедитесь, что переменная окружения BOT_TOKEN установлена.")

# Initialize bot and router
bot = Bot(token=API_TOKEN)
router = Router()

# Handler for /start command
@router.message(Command(commands=['start']))
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Отправь мне 5 строк в формате: вопрос/правильный ответ/ответ/ответ/ответ\n"
        "Каждая строка должна быть разделена переносом строки. Я создам 5 опросов-викторин!"
    )

# Handler for text messages
@router.message()
async def process_quiz_input(message: types.Message):
    # Разделяем текст на блоки вопросов, разделенных пустой строкой
    blocks = message.text.strip().split('\n\n')
    
    # Проверяем, что ровно 5 блоков вопросов
    if len(blocks) != 5:
        await message.reply("Пожалуйста, отправь ровно 5 вопросов, разделенных пустой строкой!")
        return
    
    quizzes = []
    for block in blocks:
        # Разделяем блок на строки (вопрос и ответы)
        lines = block.strip().split('\n')
        if len(lines) != 5:
            await message.reply(f"Ошибка в формате блока: '{block}'. Должно быть 5 строк: вопрос, правильный ответ и 3 неправильных ответа.")
            return
        
        question, correct_answer, *other_answers = lines
        # Собираем все ответы и перемешиваем
        answers = [correct_answer] + other_answers
        random.shuffle(answers)
        # Определяем индекс правильного ответа после перемешивания
        correct_answer_index = answers.index(correct_answer)
        
        quizzes.append({
            'question': question.strip(),
            'answers': [ans.strip() for ans in answers],
            'correct_option_id': correct_answer_index
        })
    
    # Отправляем каждый вопрос как опрос
    for quiz in quizzes:
        try:
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
            await message.reply(f"Ошибка при отправке опроса: {e}")

async def main():
    # Initialize dispatcher and register router
    dp = Dispatcher()
    dp.include_router(router)

    # Start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")

if __name__ == '__main__':
    asyncio.run(main())