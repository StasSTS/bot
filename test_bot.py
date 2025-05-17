import os
import logging
import telebot
from telebot import types
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получение токена бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не найден. Создайте файл .env с переменной BOT_TOKEN.")
    exit(1)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)

# Проверка обработки команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Тест кнопки", callback_data="test_button"))
    keyboard.add(types.InlineKeyboardButton("Тест кнопки Назад", callback_data="test_back"))
    
    bot.send_message(
        message.chat.id,
        "Тестовый бот запущен. Выберите опцию для тестирования:",
        reply_markup=keyboard
    )

# Обработчик кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "test_button":
        # Тестирование обычной кнопки
        bot.edit_message_text(
            "Вы нажали на тестовую кнопку!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        
    elif call.data == "test_back":
        # Тестирование кнопки "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Назад", callback_data="back"))
        
        bot.edit_message_text(
            "Сейчас вы нажмете кнопку Назад. Она должна вернуть вас в начальное меню.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
        
    elif call.data == "back":
        # Обработка нажатия кнопки "Назад"
        start_command(call.message)

# Запуск бота
if __name__ == "__main__":
    logger.info("Тестовый бот запущен")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}") 