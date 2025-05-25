from typing import List, Optional
import logging
import telebot
from telebot import types
from datetime import datetime

import utils
import config
from database import db
from models import Category, Product

# Общая кнопка "Назад"
BACK_BUTTON = types.InlineKeyboardButton("↩️  Назад", callback_data="back")

# Стартовые клавиатуры
def get_start_keyboard(user_id: int = None) -> types.InlineKeyboardMarkup:
    """Стартовая клавиатура с выбором режима"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Режим покупателя", callback_data="mode_customer"))
    
    # Показываем кнопку администрирования только администратору
    if user_id == config.ADMIN_USER_ID:
        keyboard.add(types.InlineKeyboardButton("Администрирование", callback_data="mode_admin"))
    
    return keyboard

# Клавиатуры для режима администратора
def get_admin_main_keyboard() -> types.InlineKeyboardMarkup:
    """Главная клавиатура администратора"""
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("Добавить категорию", callback_data="admin_add_category"),
        types.InlineKeyboardButton("Изменить", callback_data="admin_edit_category"),
        types.InlineKeyboardButton("Удалить", callback_data="admin_delete_category")
    )
    keyboard.add(
        types.InlineKeyboardButton("Добавить товар", callback_data="admin_add_product"),
        types.InlineKeyboardButton("Изменить", callback_data="admin_edit_product"),
        types.InlineKeyboardButton("Удалить", callback_data="admin_delete_product")
    )
    keyboard.add(
        types.InlineKeyboardButton("Заказы", callback_data="admin_orders"),
        types.InlineKeyboardButton("Аналитика", callback_data="admin_analytics")
    )
    keyboard.add(
        types.InlineKeyboardButton("Сохранить", callback_data="admin_save_data"),
        types.InlineKeyboardButton("Загрузить", callback_data="admin_load_data")
    )
    keyboard.add(types.InlineKeyboardButton("Вернуться к выбору режима", callback_data="back_to_start"))
    return keyboard

def get_categories_keyboard(action_prefix: str) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора категории"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры для выбора категории с префиксом: {action_prefix}")
    
    keyboard = types.InlineKeyboardMarkup()
    categories = db.get_categories()
    logger.info(f"Получено категорий: {len(categories)}")
    
    for category in categories:
        callback_data = f"{action_prefix}_{category.id}"
        logger.info(f"Добавление кнопки: {category.name} с callback_data: {callback_data}")
        keyboard.add(types.InlineKeyboardButton(category.name, callback_data=callback_data))
    
    keyboard.add(BACK_BUTTON)
    return keyboard

def get_products_keyboard(category_id: Optional[int], action_prefix: str) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора товара"""
    keyboard = types.InlineKeyboardMarkup()
    products = db.get_products(category_id)
    
    # Сортируем товары по алфавиту
    sorted_products = sorted(products, key=lambda p: p.name)
    
    for product in sorted_products:
        product_text = f"{product.name} ({utils.format_money(product.price)})"
        if not product.available:
            product_text += " [Недоступен]"
        
        callback_data = f"{action_prefix}_{product.id}"
        keyboard.add(types.InlineKeyboardButton(product_text, callback_data=callback_data))
    
    keyboard.add(BACK_BUTTON)
    return keyboard

def get_product_edit_keyboard(product_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для редактирования товара"""
    keyboard = types.InlineKeyboardMarkup()
    product = db.get_product(product_id)
    availability_text = "Снять с продажи" if product.available else "Вернуть в продажу"
    
    keyboard.add(types.InlineKeyboardButton("Изменить название", callback_data=f"edit_product_name_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Изменить цену", callback_data=f"edit_product_price_{product_id}"))
    keyboard.add(types.InlineKeyboardButton("Изменить картинку", callback_data=f"edit_product_image_{product_id}"))
    keyboard.add(types.InlineKeyboardButton(availability_text, callback_data=f"edit_product_available_{product_id}"))
    keyboard.add(BACK_BUTTON)
    return keyboard

def get_unit_selection_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора единицы измерения"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("кг", callback_data="unit_kg"),
        types.InlineKeyboardButton("шт", callback_data="unit_piece")
    )
    keyboard.add(BACK_BUTTON)
    return keyboard

def get_backup_list_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора резервной копии"""
    keyboard = types.InlineKeyboardMarkup()
    backups = db.list_backups()
    
    for backup in backups:
        keyboard.add(types.InlineKeyboardButton(backup, callback_data=f"load_backup_{backup}"))
    
    keyboard.add(BACK_BUTTON)
    return keyboard

# Клавиатуры для режима покупателя
def get_customer_main_keyboard() -> types.InlineKeyboardMarkup:
    """Главная клавиатура покупателя"""
    keyboard = types.InlineKeyboardMarkup()
    categories = db.get_categories()
    
    # Добавляем категории
    for category in categories:
        keyboard.add(types.InlineKeyboardButton(category.name, callback_data=f"category_{category.id}"))
    
    # Добавляем избранное и поиск
    keyboard.add(types.InlineKeyboardButton("❤️ Избранное", callback_data="favorites"))
    keyboard.add(types.InlineKeyboardButton("🔍 Поиск", callback_data="search"))
    
    return keyboard

def get_customer_main_keyboard_with_cart(user_id: int) -> types.InlineKeyboardMarkup:
    """Главная клавиатура покупателя с корзиной, если она не пуста"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры с корзиной для пользователя: {user_id}")
    
    keyboard = get_customer_main_keyboard()
    
    # Проверяем, не пуста ли корзина
    user = db.get_user(user_id)
    if user and user.cart:
        total = utils.calculate_cart_total(user_id)
        logger.info(f"Добавление кнопки корзины: Корзина ({utils.format_money(total)}), callback_data=cart")
        keyboard.add(types.InlineKeyboardButton(f"🛒 Корзина ({utils.format_money(total)})", callback_data="cart"))
    else:
        logger.info(f"Корзина пользователя пуста или пользователь не найден: {user_id}")
    
    return keyboard

def get_products_by_category_keyboard(category_id: int, user_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура с товарами в категории"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры с товарами категории {category_id} для пользователя: {user_id}")
    
    keyboard = types.InlineKeyboardMarkup()
    products = db.get_available_products(category_id)
    
    # Сортируем товары по алфавиту
    sorted_products = sorted(products, key=lambda p: p.name)
    
    for product in sorted_products:
        product_text = f"{product.name} - {utils.format_money(product.price)}"
        callback_data = f"product_{product.id}"
        logger.debug(f"Добавление кнопки товара: {product_text}, callback_data={callback_data}")
        keyboard.add(types.InlineKeyboardButton(product_text, callback_data=callback_data))
    
    # Добавляем кнопку назад
    keyboard.add(BACK_BUTTON)
    
    # Проверяем, не пуста ли корзина
    user = db.get_user(user_id)
    if user and user.cart:
        total = utils.calculate_cart_total(user_id)
        logger.info(f"Добавление кнопки корзины в категории: Корзина ({utils.format_money(total)}), callback_data=cart")
        keyboard.add(types.InlineKeyboardButton(f"🛒 Корзина ({utils.format_money(total)})", callback_data="cart"))
    
    return keyboard

def get_product_detail_keyboard(product: Product, user_id: int, allow_custom_quantity: bool = False) -> types.InlineKeyboardMarkup:
    """Клавиатура для детальной информации о товаре"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры детальной информации о товаре {product.id} для пользователя: {user_id}")
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Проверяем, в избранном ли товар
    user = db.get_user(user_id)
    if not user:
        logger.error(f"Пользователь не найден при создании клавиатуры товара: {user_id}")
        # Возвращаем базовую клавиатуру
        keyboard.add(BACK_BUTTON)
        return keyboard
    
    favorite_text = "Удалить из избранного" if product.id in user.favorites else "Добавить в избранное"
    favorite_callback = f"remove_favorite_{product.id}" if product.id in user.favorites else f"add_favorite_{product.id}"
    
    keyboard.add(types.InlineKeyboardButton(favorite_text, callback_data=favorite_callback))
    
    # Кнопки для добавления товара в корзину
    if product.unit == "шт":
        keyboard.add(types.InlineKeyboardButton("+1 шт", callback_data=f"add_to_cart_{product.id}_1"))
    else:
        keyboard.add(
            types.InlineKeyboardButton("+1 кг", callback_data=f"add_to_cart_{product.id}_1"),
            types.InlineKeyboardButton("+0.5 кг", callback_data=f"add_to_cart_{product.id}_0.5")
        )
        keyboard.add(
            types.InlineKeyboardButton("+0.25 кг", callback_data=f"add_to_cart_{product.id}_0.25"),
            types.InlineKeyboardButton("+0.1 кг", callback_data=f"add_to_cart_{product.id}_0.1")
        )
    # Новая кнопка для ручного ввода количества
    if allow_custom_quantity:
        keyboard.add(types.InlineKeyboardButton("Ввести количество", callback_data=f"custom_quantity_{product.id}"))
    # Кнопка для удаления товара из корзины
    keyboard.add(types.InlineKeyboardButton("Удалить из корзины", callback_data=f"remove_from_cart_{product.id}"))
    # Кнопка назад
    keyboard.add(BACK_BUTTON)
    # Корзина, если не пуста
    if user.cart:
        total = utils.calculate_cart_total(user_id)
        logger.info(f"Добавление кнопки корзины в детали товара: Корзина ({utils.format_money(total)}), callback_data=cart")
        keyboard.add(types.InlineKeyboardButton(f"🛒 Корзина ({utils.format_money(total)})", callback_data="cart"))
    return keyboard

def get_favorites_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура с избранными товарами"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры избранных товаров для пользователя: {user_id}")
    
    keyboard = types.InlineKeyboardMarkup()
    favorite_products = db.get_favorite_products(user_id)
    
    # Сортируем избранные товары по алфавиту
    sorted_favorites = sorted(favorite_products, key=lambda p: p.name)
    
    for product in sorted_favorites:
        product_text = f"{product.name} - {utils.format_money(product.price)}"
        callback_data = f"product_{product.id}"
        logger.debug(f"Добавление кнопки избранного товара: {product_text}, callback_data={callback_data}")
        keyboard.add(types.InlineKeyboardButton(product_text, callback_data=callback_data))
    
    # Добавляем кнопку назад
    keyboard.add(BACK_BUTTON)
    
    # Проверяем, не пуста ли корзина
    user = db.get_user(user_id)
    if user and user.cart:
        total = utils.calculate_cart_total(user_id)
        logger.info(f"Добавление кнопки корзины в избранное: Корзина ({utils.format_money(total)}), callback_data=cart")
        keyboard.add(types.InlineKeyboardButton(f"🛒 Корзина ({utils.format_money(total)})", callback_data="cart"))
    
    return keyboard

def get_cart_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для корзины"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры для корзины пользователя: {user_id}")
    
    try:
        keyboard = types.InlineKeyboardMarkup()
        
        # Проверяем, не пуста ли корзина
        user = db.get_user(user_id)
        if not user or not user.cart:
            logger.info(f"Корзина пользователя {user_id} пуста, возвращаем только кнопку 'Назад'")
            keyboard.add(BACK_BUTTON)
            return keyboard
        
        keyboard.add(types.InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout"))
        keyboard.add(types.InlineKeyboardButton("❌ Очистить корзину", callback_data="clear_cart"))
        keyboard.add(BACK_BUTTON)
        logger.info(f"Успешно создана клавиатура для корзины пользователя: {user_id}")
        return keyboard
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры для корзины: {str(e)}, user_id={user_id}")
        # Возвращаем простую клавиатуру с кнопкой "Назад" в случае ошибки
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(BACK_BUTTON)
        return keyboard

def get_checkout_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для оформления заказа"""
    keyboard = types.InlineKeyboardMarkup()
    user = db.get_user(user_id)
    
    # Если у пользователя есть сохраненный адрес и телефон, предлагаем использовать их
    if user.phone and user.address:
        keyboard.add(types.InlineKeyboardButton("Использовать сохраненные данные", callback_data="use_saved_data"))
    
    # Добавляем кнопку для ввода телефона
    keyboard.add(types.InlineKeyboardButton("Ввести контактные данные", callback_data="phone_input"))
    
    keyboard.add(BACK_BUTTON)
    return keyboard

def get_delivery_time_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора времени доставки"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Добавляем временные интервалы (можно настроить под требования бизнеса)
    keyboard.add(
        types.InlineKeyboardButton("10:00 - 12:00", callback_data="delivery_time_10-12"),
        types.InlineKeyboardButton("12:00 - 14:00", callback_data="delivery_time_12-14")
    )
    keyboard.add(
        types.InlineKeyboardButton("14:00 - 16:00", callback_data="delivery_time_14-16"),
        types.InlineKeyboardButton("16:00 - 18:00", callback_data="delivery_time_16-18")
    )
    keyboard.add(
        types.InlineKeyboardButton("18:00 - 20:00", callback_data="delivery_time_18-20"),
        types.InlineKeyboardButton("20:00 - 22:00", callback_data="delivery_time_20-22")
    )
    
    keyboard.add(BACK_BUTTON)
    return keyboard

# Клавиатуры для работы с заказами
def get_orders_list_keyboard(orders: List, filter_type: str = "all", current_page: int = 1, total_pages: int = 1, page_size: int = 10) -> types.InlineKeyboardMarkup:
    """Клавиатура со списком заказов"""
    logger = logging.getLogger(__name__)
    logger.info(f"Создание клавиатуры для списка заказов, количество заказов: {len(orders)}, фильтр: {filter_type}, страница: {current_page}/{total_pages}")
    
    try:
        keyboard = types.InlineKeyboardMarkup()
        
        # Если заказов нет
        if not orders:
            keyboard.add(types.InlineKeyboardButton("Нет заказов", callback_data="no_action"))
        else:
            # Отображаем заказы текущей страницы
            for order in orders:
                # Проверка наличия необходимых атрибутов
                if not hasattr(order, "id") or not hasattr(order, "created_at") or not hasattr(order, "status"):
                    logger.warning(f"Объект заказа не содержит необходимых атрибутов: {order}")
                    continue
                
                try:
                    # Формируем текст кнопки: номер заказа, дата, статус
                    date_str = datetime.fromisoformat(order.created_at).strftime("%d.%m.%Y")
                    status_str = "✅" if order.status == "completed" else "🔄"
                    
                    button_text = f"Заказ #{order.id} от {date_str} {status_str}"
                    callback_data = f"view_order_{order.id}"
                    
                    # Проверка длины callback_data, Telegram API ограничивает до 64 байт
                    if len(callback_data.encode('utf-8')) > 64:
                        logger.warning(f"Callback data слишком длинный: {callback_data}, обрезаем")
                        callback_data = callback_data[:64]
                    
                    keyboard.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
                except Exception as e:
                    logger.error(f"Ошибка при создании кнопки для заказа {getattr(order, 'id', 'unknown')}: {str(e)}")
                    continue
        
        # Добавляем кнопки пагинации, если страниц больше одной
        if total_pages > 1:
            pagination_row = []
            
            # Кнопка "Назад" (неактивна на первой странице)
            if current_page > 1:
                pagination_row.append(types.InlineKeyboardButton("⬅️", callback_data="page_prev"))
                
            # Текущая страница/всего страниц
            pagination_row.append(types.InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="no_action"))
            
            # Кнопка "Вперед" (неактивна на последней странице)
            if current_page < total_pages:
                pagination_row.append(types.InlineKeyboardButton("➡️", callback_data="page_next"))
                
            keyboard.add(*pagination_row)
        
        # Добавляем кнопки для выбора размера страницы
        page_size_row = []
        for size in [10, 20]:
            btn_text = f"🔘 {size} заказов" if size == page_size else f"{size} заказов"
            page_size_row.append(types.InlineKeyboardButton(btn_text, callback_data=f"page_size_{size}"))
        
        keyboard.add(*page_size_row)
        
        # Добавляем кнопки фильтрации
        filter_row = []
        
        # Кнопка "Все заказы" активна, если выбран этот фильтр
        all_btn = types.InlineKeyboardButton(
            "🔘 Все" if filter_type == "all" else "Все", 
            callback_data="filter_orders_all"
        )
        
        # Кнопка "Новые" активна, если выбран этот фильтр
        new_btn = types.InlineKeyboardButton(
            "🔘 Новые" if filter_type == "new" else "Новые", 
            callback_data="filter_orders_new"
        )
        
        # Кнопка "Завершенные" активна, если выбран этот фильтр
        completed_btn = types.InlineKeyboardButton(
            "🔘 Завершенные" if filter_type == "completed" else "Завершенные", 
            callback_data="filter_orders_completed"
        )
        
        filter_row.extend([all_btn, new_btn, completed_btn])
        keyboard.add(*filter_row)
        
        # Сортировка
        keyboard.add(types.InlineKeyboardButton("📅 Сортировать по дате", callback_data="sort_orders_date"))
        keyboard.add(types.InlineKeyboardButton("👤 Сортировать по пользователям", callback_data="sort_orders_user"))
        
        # Кнопка "Назад"
        keyboard.add(BACK_BUTTON)
        
        logger.info("Клавиатура для списка заказов успешно создана")
        return keyboard
    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры для списка заказов: {str(e)}")
        # Возвращаем простую клавиатуру только с кнопкой "Назад" в случае ошибки
        simple_keyboard = types.InlineKeyboardMarkup()
        simple_keyboard.add(BACK_BUTTON)
        return simple_keyboard

def get_order_detail_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для просмотра деталей заказа"""
    keyboard = types.InlineKeyboardMarkup()
    order = db.get_order(order_id)
    
    # Статус заказа (завершен/не завершен)
    if order.status == "completed":
        keyboard.add(types.InlineKeyboardButton("Reopened заказ", callback_data=f"reopen_order_{order_id}"))
    else:
        keyboard.add(types.InlineKeyboardButton("Завершить заказ", callback_data=f"complete_order_{order_id}"))
    
    # Кнопка назад
    keyboard.add(types.InlineKeyboardButton("↩️ К списку заказов", callback_data="back_to_orders"))
    keyboard.add(BACK_BUTTON)
    
    return keyboard

def get_phone_input_keyboard(current_phone: str = "") -> types.InlineKeyboardMarkup:
    """Создает виртуальную клавиатуру для ввода телефона
    
    Args:
        current_phone: Текущий введенный телефон (без маски)
    
    Returns:
        Клавиатура с цифрами и функциональными кнопками
    """
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    
    # Добавляем цифры от 1 до 9
    buttons_row = []
    for i in range(1, 10):
        btn = types.InlineKeyboardButton(str(i), callback_data=f"phone_digit_{i}")
        buttons_row.append(btn)
        if len(buttons_row) == 3:
            keyboard.add(*buttons_row)
            buttons_row = []
    
    # Добавляем кнопку "0" в центре последнего ряда
    keyboard.add(
        types.InlineKeyboardButton("⬅️", callback_data="phone_delete"),
        types.InlineKeyboardButton("0", callback_data="phone_digit_0"),
        types.InlineKeyboardButton("✅", callback_data="phone_submit")
    )
    
    # Добавляем кнопку "Назад"
    keyboard.add(BACK_BUTTON)
    
    return keyboard 