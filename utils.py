import os
import re
import logging
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime

from telebot import types
from telebot.apihelper import ApiTelegramException

import config
from database import db
from models import Product, CartItem

# Шаблон для проверки номера телефона
PHONE_PATTERN = r'^\+7-\d{3}-\d{3}-\d{2}-\d{2}$'

def format_phone(phone: str) -> str:
    """
    Форматирует номер телефона в формат +7-XXX-XXX-XX-XX
    """
    # Удаляем все символы, кроме цифр
    digits = re.sub(r'\D', '', phone)
    
    # Если номер начинается с 8 или 7, заменяем на +7
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    if not digits.startswith('7'):
        digits = '7' + digits
    
    # Проверяем, что после кода страны (7) есть ровно 10 цифр
    if len(digits) > 11:
        digits = digits[:11]  # Берем только первые 11 цифр (7 + 10 цифр номера)
    
    # Форматируем номер
    if len(digits) >= 11:
        return f"+{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return phone

def validate_phone(phone: str) -> bool:
    """
    Проверяет, соответствует ли номер телефона шаблону +7-XXX-XXX-XX-XX
    и содержит ли он ровно 10 цифр после кода страны
    """
    if not re.match(PHONE_PATTERN, phone):
        return False
    
    # Дополнительная проверка на количество цифр
    digits = re.sub(r'\D', '', phone)
    return len(digits) == 11 and digits.startswith('7')  # 7 + 10 цифр номера

def save_image(message: types.Message, file_path: str) -> Optional[str]:
    """
    Сохраняет изображение в указанную директорию
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file_info = message.bot.get_file(message.photo[-1].file_id)
        downloaded_file = message.bot.download_file(file_info.file_path)
        
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        return file_path
    except Exception as e:
        print(f"Ошибка сохранения изображения: {e}")
        return None

def format_money(amount: float) -> str:
    """
    Форматирует денежную сумму в удобочитаемый вид
    """
    return f"{amount:.2f} ₽"

def format_money_simple(amount: float) -> str:
    """
    Форматирует денежную сумму без десятичных знаков, если они равны нулю
    Например: 100.00 -> 100 ₽, 100.50 -> 100.5 ₽
    """
    if amount == int(amount):
        return f"{int(amount)} ₽"
    return f"{amount:.2f}".rstrip('0').rstrip('.') + " ₽"

def format_phone_with_mask(digits: str) -> str:
    """
    Форматирует цифры телефона в маску ввода для визуализации
    
    Args:
        digits: Строка только с цифрами (без +7 и других символов)
        
    Returns:
        Форматированная строка вида: "XXX-XXX-XX-XX" где X - цифра или "_"
    """
    # Очищаем от всех нецифровых символов
    clean_digits = ''.join(filter(str.isdigit, digits))
    
    # Ограничиваем до 10 цифр
    if len(clean_digits) > 10:
        clean_digits = clean_digits[:10]
    
    # Создаем шаблон маски
    mask = ["_", "_", "_", "-", "_", "_", "_", "-", "_", "_", "-", "_", "_"]
    
    # Заполняем маску имеющимися цифрами
    for i, digit in enumerate(clean_digits):
        if i < 3:
            mask[i] = digit
        elif i < 6:
            mask[i+1] = digit
        elif i < 8:
            mask[i+2] = digit
        elif i < 10:
            mask[i+3] = digit
    
    return "".join(mask)

def format_date(date_str: str, include_time: bool = True) -> str:
    """
    Форматирует дату из формата ISO в удобный для чтения формат.
    
    Args:
        date_str: Строка с датой в формате ISO
        include_time: Включать ли время в результат
        
    Returns:
        Форматированная строка даты
    """
    try:
        dt = datetime.fromisoformat(date_str)
        if include_time:
            return dt.strftime("%d.%m.%Y %H:%M")
        else:
            return dt.strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return date_str

def get_product_details(product: Product) -> str:
    """
    Форматирует детальную информацию о товаре
    """
    unit_text = "шт" if product.unit == "шт" else "кг"
    return f"{product.name} - {format_money(product.price)}/{unit_text}"

def calculate_cart_total(user_id: int) -> float:
    """
    Рассчитывает общую стоимость корзины пользователя
    """
    user = db.get_user(user_id)
    total = 0.0
    
    for item in user.cart:
        product = db.get_product(item.product_id)
        if product:
            total += product.price * item.quantity
    
    return total

def get_cart_details(user_id: int) -> Tuple[str, float]:
    """
    Возвращает детальную информацию о корзине пользователя и общую стоимость
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Получение деталей корзины для пользователя: {user_id}")
    
    try:
        user = db.get_user(user_id)
        if not user:
            logger.error(f"Пользователь не найден при получении деталей корзины: {user_id}")
            return "Корзина недоступна", 0.0
        
        cart_items = []
        total = 0.0
        
        if not user.cart:
            logger.info(f"Корзина пользователя {user_id} пуста")
            return "Корзина пуста", 0.0
        
        for item in user.cart:
            try:
                product = db.get_product(item.product_id)
                if not product:
                    logger.warning(f"Товар не найден в корзине: product_id={item.product_id}")
                    continue
                
                price = product.price * item.quantity
                unit_text = "шт" if product.unit == "шт" else "кг"
                
                # Форматируем количество с округлением вверх для веса
                import math
                formatted_quantity = item.quantity
                if product.unit == "кг" and isinstance(item.quantity, float):
                    # Округляем вверх до двух знаков после точки
                    # Умножаем на 100, округляем вверх, делим на 100
                    formatted_quantity = math.ceil(item.quantity * 100) / 100
                
                # Изменяем формат отображения товара в корзине
                # Используем format_money_simple для цены за единицу
                cart_items.append(f"{product.name} {format_money_simple(product.price)}/{unit_text} x {formatted_quantity} {unit_text} = {format_money_simple(price)}")
                total += price
            except Exception as e:
                logger.error(f"Ошибка при обработке товара в корзине: {str(e)}, product_id={item.product_id}")
                continue
        
        cart_text = "\n".join(cart_items) if cart_items else "Корзина пуста"
        logger.info(f"Успешно получены детали корзины для пользователя {user_id}: {len(cart_items)} товаров, всего: {total}")
        return cart_text, total
    except Exception as e:
        logger.error(f"Ошибка при получении деталей корзины: {str(e)}, user_id={user_id}")
        return "Корзина недоступна", 0.0

def update_user_data(message: types.Message) -> None:
    """
    Обновляет данные пользователя
    """
    user_id = message.from_user.id
    username = message.from_user.username
    
    user = db.get_user(user_id)
    if username and user.username != username:
        db.update_user(user_id, username=username)

def generate_analytics() -> Dict[str, Any]:
    """
    Генерирует аналитические данные
    """
    analytics = {
        "popular_products": get_popular_products(),
        "seasonal_products": get_seasonal_products(),
        "active_customers": get_active_customers()
    }
    return analytics

def get_popular_products(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Возвращает список самых популярных товаров
    """
    # Получаем все заказы и подсчитываем количество каждого товара
    product_counts = {}
    for order in db.get_orders():
        for item in order.items:
            product_id = item.product_id
            quantity = item.quantity
            
            if product_id not in product_counts:
                product_counts[product_id] = 0
            product_counts[product_id] += quantity
    
    # Сортируем по популярности
    popular_products = []
    for product_id, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
        product = db.get_product(product_id)
        if product:
            popular_products.append({
                "id": product.id,
                "name": product.name,
                "count": count,
                "unit": product.unit
            })
    
    return popular_products

def get_seasonal_products(limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Возвращает список самых популярных товаров по сезонам
    """
    # Получаем все заказы и группируем их по сезонам
    seasons = {
        "winter": [],  # Декабрь, Январь, Февраль
        "spring": [],  # Март, Апрель, Май
        "summer": [],  # Июнь, Июль, Август
        "autumn": []   # Сентябрь, Октябрь, Ноябрь
    }
    
    for order in db.get_orders():
        try:
            date = datetime.fromisoformat(order.created_at)
            month = date.month
            
            if month in [12, 1, 2]:
                season = "winter"
            elif month in [3, 4, 5]:
                season = "spring"
            elif month in [6, 7, 8]:
                season = "summer"
            else:
                season = "autumn"
            
            seasons[season].extend(order.items)
        except:
            continue
    
    # Подсчитываем популярность товаров в каждом сезоне
    seasonal_products = {}
    for season, items in seasons.items():
        product_counts = {}
        for item in items:
            product_id = item.product_id
            quantity = item.quantity
            
            if product_id not in product_counts:
                product_counts[product_id] = 0
            product_counts[product_id] += quantity
        
        # Сортируем по популярности
        season_products = []
        for product_id, count in sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
            product = db.get_product(product_id)
            if product:
                season_products.append({
                    "id": product.id,
                    "name": product.name,
                    "count": count,
                    "unit": product.unit
                })
        
        seasonal_products[season] = season_products
    
    return seasonal_products

def get_active_customers(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Возвращает список самых активных покупателей
    """
    # Подсчитываем количество заказов для каждого пользователя
    user_orders = {}
    for order in db.get_orders():
        user_id = order.user_id
        if user_id not in user_orders:
            user_orders[user_id] = {
                "order_count": 0,
                "total_spent": 0.0
            }
        user_orders[user_id]["order_count"] += 1
        
        # Подсчитываем общую сумму заказов
        for item in order.items:
            product = db.get_product(item.product_id)
            if product:
                user_orders[user_id]["total_spent"] += product.price * item.quantity
    
    # Сортируем по количеству заказов
    active_customers = []
    for user_id, data in sorted(user_orders.items(), key=lambda x: x[1]["order_count"], reverse=True)[:limit]:
        user = db.get_user(user_id)
        if user:
            active_customers.append({
                "id": user.id,
                "username": user.username,
                "order_count": data["order_count"],
                "total_spent": data["total_spent"]
            })
    
    return active_customers

def notify_admin_about_new_order(bot, order_id: int) -> None:
    """
    Отправляет уведомление администратору о новом заказе.
    
    Args:
        bot: Экземпляр телеграм-бота
        order_id: ID созданного заказа
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Отправка уведомления администратору о новом заказе #{order_id}")
    
    try:
        # Получаем информацию о заказе
        order = db.get_order(order_id)
        if not order:
            logger.error(f"Не удалось найти заказ с ID {order_id} для уведомления администратора")
            return
        
        # Получаем информацию о пользователе
        user = db.get_user(order.user_id)
        user_info = f"@{user.username}" if user and user.username else f"ID: {order.user_id}"
        
        # Формируем текст уведомления
        text = (
            f"🔔 *НОВЫЙ ЗАКАЗ #{order.id}*\n\n"
            f"👤 Покупатель: {user_info}\n"
            f"📱 Телефон: {order.phone}\n"
            f"🏠 Адрес: {order.address}\n"
            f"⏰ Время доставки: {order.delivery_time or 'Не указано'}\n"
            f"💰 Сумма заказа: {format_money(order.total)}\n\n"
            f"📦 Товары в заказе:"
        )
        
        # Добавляем информацию о товарах
        total = 0
        for i, item in enumerate(order.items, 1):
            product = db.get_product(item.product_id)
            if product:
                price = product.price * item.quantity
                total += price
                text += f"\n{i}. {product.name} - {item.quantity} {product.unit} × {format_money(product.price)} = {format_money(price)}"
        
        # Формируем клавиатуру с кнопкой перехода к заказу
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Просмотреть заказ", callback_data=f"view_order_{order.id}"))
        
        # Отправляем уведомление администратору
        try:
            bot.send_message(
                chat_id=config.ADMIN_USER_ID,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            logger.info(f"Отправлено уведомление администратору о новом заказе #{order.id}")
        except ApiTelegramException as e:
            # Если возникла ошибка Telegram API (например, неверный синтаксис разметки)
            logger.error(f"Ошибка Telegram API при отправке уведомления: {str(e)}")
            # Попробуем отправить без разметки
            try:
                plain_text = text.replace('*', '')
                bot.send_message(
                    chat_id=config.ADMIN_USER_ID,
                    text=plain_text,
                    reply_markup=keyboard
                )
                logger.info(f"Отправлено уведомление администратору (без разметки) о новом заказе #{order.id}")
            except Exception as e2:
                logger.error(f"Критическая ошибка при отправке уведомления без разметки: {str(e2)}")
    except Exception as e:
        logger.error(f"Общая ошибка при отправке уведомления администратору: {str(e)}") 