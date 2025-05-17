import os
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

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я тестовый бот для проверки библиотеки telebot.")

print("Тест импорта библиотеки telebot успешно пройден!")
print(f"Библиотека telebot версии {telebot.__version__} успешно импортирована.")
print("Теперь можно запустить бота через main.py") 