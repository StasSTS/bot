import os
import logging
import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from dotenv import load_dotenv

import admin
from states import BotStates
import keyboards
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден. Создайте файл .env с переменной BOT_TOKEN.")
    exit(1)

# Создание экземпляра бота
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)

# Команда /start для начала тестирования
@bot.message_handler(commands=['start'])
def start_command(message):
    # Создаем тестовую категорию, если её нет
    categories = db.get_categories()
    if not categories:
        db.add_category("Тестовая категория")
        logger.info("Создана тестовая категория")
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Тест редактирования категории", callback_data="test_edit_category"))
    
    bot.send_message(
        message.chat.id,
        "Тестовый скрипт для проверки функций администратора",
        reply_markup=keyboard
    )

# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)
    
    if call.data == "test_edit_category":
        # Эмулируем начало процесса редактирования категории
        logger.info("Тестирование функции редактирования категории")
        bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
        admin.edit_category_select(bot, call)
    
    # Обработка выбора категории для редактирования
    elif call.data.startswith("edit_category_"):
        logger.info(f"Обработка выбора категории для редактирования: {call.data}")
        # Проверка текущего состояния
        current_state = bot.get_state(call.from_user.id, call.message.chat.id)
        logger.info(f"Текущее состояние: {current_state}")
        
        # Вызываем функцию редактирования
        admin.edit_category_name_input(bot, call)
    
    # Обработка кнопки "Назад"
    elif call.data == "back":
        logger.info("Обработка кнопки 'Назад'")
        current_state = bot.get_state(call.from_user.id, call.message.chat.id)
        logger.info(f"Текущее состояние: {current_state}")
        
        # Вернуться к начальному экрану
        start_command(call.message)

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    current_state = bot.get_state(user_id, message.chat.id)
    logger.info(f"Обработка текстового сообщения, текущее состояние: {current_state}")
    
    # Обработка ввода нового имени категории
    if current_state == BotStates.CATEGORY_EDIT_NAME_INPUT.name:
        logger.info("Обработка ввода нового имени категории")
        admin.edit_category_name_save(bot, message)

# Запуск бота
if __name__ == "__main__":
    logger.info("Тестовый скрипт для проверки функций администратора запущен")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}") 