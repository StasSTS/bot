import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID администратора (замените на свой ID)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))  # Временная заглушка, необходимо заменить на реальный ID

# Пути к файлам данных
DATA_DIR = "data"
CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# Создание директорий, если они не существуют
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True) 