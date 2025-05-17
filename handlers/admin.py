from typing import Dict, Any, Optional
import os
import telebot
from telebot import types
import logging
from datetime import datetime

import keyboards
import utils
import config
from database import db
from states import BotStates

# Состояния для администратора
(
    CATEGORY_NAME_INPUT, 
    CATEGORY_EDIT_SELECT,
    CATEGORY_EDIT_NAME_INPUT,
    CATEGORY_DELETE_SELECT,
    PRODUCT_CATEGORY_SELECT,
    PRODUCT_NAME_INPUT,
    PRODUCT_PRICE_INPUT,
    PRODUCT_UNIT_SELECT,
    PRODUCT_IMAGE_INPUT,
    PRODUCT_EDIT_SELECT,
    PRODUCT_EDIT_MENU,
    PRODUCT_EDIT_NAME_INPUT,
    PRODUCT_EDIT_PRICE_INPUT,
    PRODUCT_EDIT_IMAGE_INPUT,
    PRODUCT_DELETE_SELECT,
    BACKUP_SELECT
) = range(16)

def admin_main(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработчик для главного меню администратора."""
    bot.answer_callback_query(call.id)
    
    bot.edit_message_text(
        "Панель администратора",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_admin_main_keyboard()
    )
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)

def back_to_admin_main(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Вернуться в главное меню администратора."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
    
    bot.edit_message_text(
        "Панель администратора",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_admin_main_keyboard()
    )

# Обработчики для категорий
def add_category_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало процесса добавления категории."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние CATEGORY_NAME_INPUT
    bot.set_state(call.from_user.id, BotStates.CATEGORY_NAME_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        "Введите название новой категории:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

# Функция для добавления товара
def add_product_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало процесса добавления товара."""
    bot.answer_callback_query(call.id)
    
    # Проверяем, есть ли доступные категории
    categories = db.get_categories()
    if not categories:
        bot.edit_message_text(
            "Сначала создайте хотя бы одну категорию!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние PRODUCT_CATEGORY_SELECT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_CATEGORY_SELECT, call.message.chat.id)
    
    bot.edit_message_text(
        "Выберите категорию для нового товара:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_categories_keyboard("product_category")
    )

def product_category_selected(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка выбора категории для товара."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID категории из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        bot.edit_message_text(
            "Ошибка при выборе категории.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    category_id = int(data_parts[2])
    category = db.get_category(category_id)
    
    if not category:
        bot.edit_message_text(
            "Выбранная категория не найдена.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Сохраняем ID категории в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['product_category_id'] = category_id
    
    # Устанавливаем состояние PRODUCT_NAME_INPUT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_NAME_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Выбрана категория: {category.name}\n"
        f"Введите название товара:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def product_name_input(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка ввода названия товара."""
    name = message.text.strip()
    
    # Проверяем, что название не пустое
    if not name:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Название не может быть пустым. Пожалуйста, введите название товара:",
            reply_markup=keyboard
        )
        return
    
    # Сохраняем название товара в данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['product_name'] = name
    
    # Устанавливаем состояние PRODUCT_PRICE_INPUT
    bot.set_state(message.from_user.id, BotStates.PRODUCT_PRICE_INPUT, message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.send_message(
        message.chat.id,
        f"Название товара: {name}\n"
        f"Введите цену товара (в рублях, например: 99.90):",
        reply_markup=keyboard
    )

def product_price_input(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка ввода цены товара."""
    price_text = message.text.strip()
    
    try:
        # Пробуем преобразовать введенную цену в число с плавающей точкой
        price = float(price_text.replace(',', '.'))
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
    except ValueError:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Неверный формат цены. Пожалуйста, введите положительное число (например: 99.90):",
            reply_markup=keyboard
        )
        return
    
    # Сохраняем цену товара в данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['product_price'] = price
        product_name = data.get('product_name', '')
    
    # Устанавливаем состояние PRODUCT_UNIT_SELECT
    bot.set_state(message.from_user.id, BotStates.PRODUCT_UNIT_SELECT, message.chat.id)
    
    bot.send_message(
        message.chat.id,
        f"Название: {product_name}\n"
        f"Цена: {utils.format_money(price)}\n"
        f"Выберите единицу измерения:",
        reply_markup=keyboards.get_unit_selection_keyboard()
    )

def product_unit_selected(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка выбора единицы измерения товара."""
    bot.answer_callback_query(call.id)
    
    # Получаем выбранную единицу измерения из callback_data
    unit_data = call.data.split("_")[1]
    
    # Преобразуем в формат для сохранения в БД
    unit = "кг" if unit_data == "kg" else "шт"
    
    # Сохраняем единицу измерения в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['product_unit'] = unit
        product_name = data.get('product_name', '')
        product_price = data.get('product_price', 0)
    
    # Устанавливаем состояние PRODUCT_IMAGE_INPUT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_IMAGE_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад" и кнопкой "Без изображения"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Без изображения", callback_data="skip_image"))
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Название: {product_name}\n"
        f"Цена: {utils.format_money(product_price)}\n"
        f"Единица измерения: {unit}\n\n"
        f"Отправьте изображение товара или нажмите 'Без изображения':",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def product_image_skipped(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка пропуска загрузки изображения товара."""
    bot.answer_callback_query(call.id)
    
    # Получаем данные о товаре из состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        category_id = data.get('product_category_id')
        name = data.get('product_name')
        price = data.get('product_price')
        unit = data.get('product_unit')
    
    # Проверяем, что все необходимые данные присутствуют
    if not all([category_id, name, price, unit]):
        bot.edit_message_text(
            "Ошибка: не все данные о товаре были заполнены.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Добавляем товар без изображения
    product = db.add_product(name, category_id, price, unit)
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
    
    if product:
        bot.edit_message_text(
            f"Товар '{product.name}' успешно добавлен!\n"
            f"Цена: {utils.format_money(product.price)}\n"
            f"Единица измерения: {product.unit}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
    else:
        bot.edit_message_text(
            "Ошибка при добавлении товара.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def product_image_uploaded(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка загрузки изображения товара."""
    # Получаем данные о товаре из состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        category_id = data.get('product_category_id')
        name = data.get('product_name')
        price = data.get('product_price')
        unit = data.get('product_unit')
    
    # Проверяем, что все необходимые данные присутствуют
    if not all([category_id, name, price, unit]):
        bot.send_message(
            message.chat.id,
            "Ошибка: не все данные о товаре были заполнены.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем информацию о фото
    photo = message.photo[-1]  # Берем последнее (самое качественное) фото
    file_id = photo.file_id
    
    # Добавляем товар с изображением
    product = db.add_product(name, category_id, price, unit, image_path=file_id)
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(message.from_user.id, BotStates.ADMIN_MODE, message.chat.id)
    
    if product:
        bot.send_message(
            message.chat.id,
            f"Товар '{product.name}' успешно добавлен с изображением!\n"
            f"Цена: {utils.format_money(product.price)}\n"
            f"Единица измерения: {product.unit}",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Ошибка при добавлении товара.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def add_category_name(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка ввода названия категории."""
    name = message.text.strip()
    
    # Проверяем, что название не пустое
    if not name:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Название не может быть пустым. Пожалуйста, введите название категории:",
            reply_markup=keyboard
        )
        return
    
    # Добавляем категорию
    category = db.add_category(name)
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(message.from_user.id, BotStates.ADMIN_MODE, message.chat.id)
    
    bot.send_message(
        message.chat.id,
        f"Категория '{category.name}' успешно добавлена!",
        reply_markup=keyboards.get_admin_main_keyboard()
    )

def edit_category_select(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Выбор категории для редактирования."""
    bot.answer_callback_query(call.id)
    logger = logging.getLogger(__name__)
    logger.info(f"Вызвана функция edit_category_select: {call.data}")
    
    categories = db.get_categories()
    if not categories:
        bot.edit_message_text(
            "Нет доступных категорий для редактирования.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние CATEGORY_EDIT_SELECT
    bot.set_state(call.from_user.id, BotStates.CATEGORY_EDIT_SELECT, call.message.chat.id)
    logger.info(f"Установлено состояние: {BotStates.CATEGORY_EDIT_SELECT.name}")
    
    keyboard = keyboards.get_categories_keyboard("edit_category")
    logger.info(f"Создана клавиатура с кнопками: {[btn.callback_data for row in keyboard.keyboard for btn in row]}")
    
    bot.edit_message_text(
        "Выберите категорию для редактирования:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_category_name_input(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Запрос нового названия для категории."""
    bot.answer_callback_query(call.id)
    logger = logging.getLogger(__name__)
    logger.info(f"Вызвана функция edit_category_name_input: {call.data}")
    
    # Получаем ID категории из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        logger.error(f"Неверный формат callback_data: {call.data}")
        bot.edit_message_text(
            "Ошибка при выборе категории.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    category_id = int(data_parts[2])
    logger.info(f"Извлечен ID категории: {category_id}")
    category = db.get_category(category_id)
    
    if not category:
        logger.error(f"Категория с ID {category_id} не найдена")
        bot.edit_message_text(
            "Выбранная категория не найдена.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние CATEGORY_EDIT_NAME_INPUT
    bot.set_state(call.from_user.id, BotStates.CATEGORY_EDIT_NAME_INPUT, call.message.chat.id)
    logger.info(f"Установлено состояние: {BotStates.CATEGORY_EDIT_NAME_INPUT.name}")
    
    # Сохраняем ID категории в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['edit_category_id'] = category_id
    logger.info(f"Сохранен ID категории {category_id} в данных состояния")
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Текущее название категории: '{category.name}'\n"
        f"Введите новое название:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_category_name_save(bot: telebot.TeleBot, message: types.Message) -> None:
    """Сохранение нового названия категории."""
    new_name = message.text.strip()
    
    # Проверяем, что название не пустое
    if not new_name:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Название не может быть пустым. Пожалуйста, введите новое название категории:",
            reply_markup=keyboard
        )
        return
    
    # Получаем ID категории из данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        category_id = data.get('edit_category_id')
    
    if not category_id:
        bot.send_message(
            message.chat.id,
            "Ошибка: ID категории не найден.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Обновляем название категории
    category = db.update_category(category_id, new_name)
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(message.from_user.id, BotStates.ADMIN_MODE, message.chat.id)
    
    if category:
        bot.send_message(
            message.chat.id,
            f"Категория успешно переименована в '{category.name}'!",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "Ошибка при обновлении категории.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def delete_category_select(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Выбор категории для удаления."""
    bot.answer_callback_query(call.id)
    
    categories = db.get_categories()
    if not categories:
        bot.edit_message_text(
            "Нет доступных категорий для удаления.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние CATEGORY_DELETE_SELECT
    bot.set_state(call.from_user.id, BotStates.CATEGORY_DELETE_SELECT, call.message.chat.id)
    
    bot.edit_message_text(
        "Выберите категорию для удаления (внимание: будут удалены все товары в этой категории):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_categories_keyboard("delete_category")
    )

def delete_category_confirm(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Подтверждение удаления категории."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID категории из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        bot.edit_message_text(
            "Ошибка при выборе категории.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    category_id = int(data_parts[2])
    category = db.get_category(category_id)
    
    if not category:
        bot.edit_message_text(
            "Выбранная категория не найдена.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние ADMIN_MODE
    bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
    
    # Удаляем категорию
    if db.delete_category(category_id):
        bot.edit_message_text(
            f"Категория '{category.name}' и все её товары успешно удалены!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
    else:
        bot.edit_message_text(
            "Ошибка при удалении категории.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def edit_product_select(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Выбор товара для редактирования."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние PRODUCT_EDIT_SELECT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_EDIT_SELECT, call.message.chat.id)
    
    bot.edit_message_text(
        "Выберите категорию товара для редактирования:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_categories_keyboard("edit_category_products")
    )

def show_products_for_edit(bot: telebot.TeleBot, call: types.CallbackQuery, category_id: int) -> None:
    """Показать список товаров категории для редактирования."""
    logger = logging.getLogger(__name__)
    logger.info(f"Выбор товара для редактирования в категории {category_id}")
    
    bot.answer_callback_query(call.id)
    
    # Получаем категорию
    category = db.get_category(category_id)
    if not category:
        logger.error(f"Категория не найдена: {category_id}")
        bot.edit_message_text(
            "Категория не найдена",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем все товары в категории
    products = db.get_products(category_id)
    if not products:
        bot.edit_message_text(
            f"В категории '{category.name}' нет товаров.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_categories_keyboard("edit_category_products")
        )
        return
    
    # Создаем клавиатуру с товарами
    keyboard = types.InlineKeyboardMarkup()
    for product in products:
        status = "✅" if product.available else "❌"
        keyboard.add(types.InlineKeyboardButton(
            f"{product.name} [{status}]", 
            callback_data=f"edit_product_{product.id}"
        ))
    
    # Добавляем кнопку "Назад"
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Товары в категории '{category.name}'.\nВыберите товар для редактирования:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_product_menu(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать меню редактирования товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data или из данных состояния
    product_id = None
    data_parts = call.data.split("_")
    
    if call.data.startswith("edit_product_") and len(data_parts) >= 3:
        # Если вызван через выбор товара для редактирования
        product_id = int(data_parts[2])
    else:
        # Если вызван через кнопку "Назад", получаем ID из данных состояния
        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
            product_id = data.get('edit_product_id')
            if not product_id:
                product_id = data.get('current_product_id')
    
    if not product_id:
        logger.error(f"Не удалось получить ID товара из callback_data: {call.data} или из данных состояния")
        bot.edit_message_text(
            "Ошибка: не удалось определить ID товара",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Сохраняем ID товара в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['current_product_id'] = product_id
    
    # Устанавливаем состояние PRODUCT_EDIT_MENU
    bot.set_state(call.from_user.id, BotStates.PRODUCT_EDIT_MENU, call.message.chat.id)
    
    # Получаем клавиатуру для редактирования товара
    keyboard = keyboards.get_product_edit_keyboard(product_id)
    
    # Формируем информацию о товаре
    category = db.get_category(product.category_id)
    category_name = category.name if category else "Категория не найдена"
    
    availability = "В наличии ✅" if product.available else "Отсутствует ❌"
    
    bot.edit_message_text(
        f"📋 Информация о товаре:\n\n"
        f"📦 Название: {product.name}\n"
        f"🏷️ Категория: {category_name}\n"
        f"💰 Цена: {utils.format_money(product.price)}/{product.unit}\n"
        f"📊 Статус: {availability}\n\n"
        f"Выберите действие:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def toggle_product_availability(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Переключить статус доступности товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 4:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    product_id = int(data_parts[3])
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Изменяем статус товара
    new_status = not product.available
    db.update_product_availability(product_id, new_status)
    
    # Получаем обновленный товар
    updated_product = db.get_product(product_id)
    
    # Показываем меню редактирования товара с обновленной информацией
    category = db.get_category(updated_product.category_id)
    category_name = category.name if category else "Категория не найдена"
    
    availability = "В наличии ✅" if updated_product.available else "Отсутствует ❌"
    status_changed = "Товар добавлен в каталог" if updated_product.available else "Товар скрыт из каталога"
    
    # Получаем клавиатуру для редактирования товара
    keyboard = keyboards.get_product_edit_keyboard(product_id)
    
    bot.edit_message_text(
        f"📋 Информация о товаре:\n\n"
        f"📦 Название: {updated_product.name}\n"
        f"🏷️ Категория: {category_name}\n"
        f"💰 Цена: {utils.format_money(updated_product.price)}/{updated_product.unit}\n"
        f"📊 Статус: {availability}\n\n"
        f"✅ {status_changed}\n\n"
        f"Выберите действие:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_product_name_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало процесса изменения названия товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 4:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    product_id = int(data_parts[3])
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Сохраняем ID товара в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['edit_product_id'] = product_id
        data['current_product_id'] = product_id
    
    # Устанавливаем состояние PRODUCT_EDIT_NAME_INPUT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_EDIT_NAME_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Текущее название товара: '{product.name}'\n"
        f"Введите новое название:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_product_name_save(bot: telebot.TeleBot, message: types.Message) -> None:
    """Сохранение нового названия товара."""
    logger = logging.getLogger(__name__)
    
    new_name = message.text.strip()
    
    # Проверяем, что название не пустое
    if not new_name:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Название не может быть пустым. Пожалуйста, введите новое название товара:",
            reply_markup=keyboard
        )
        return
    
    # Получаем ID товара из данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        product_id = data.get('edit_product_id')
    
    if not product_id:
        logger.error("ID товара не найден в данных состояния")
        bot.send_message(
            message.chat.id,
            "Ошибка: ID товара не найден в данных состояния.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем старое название товара для сообщения
    product = db.get_product(product_id)
    old_name = product.name if product else "неизвестно"
    
    # Обновляем название товара
    updated_product = db.update_product(product_id, name=new_name)
    
    if not updated_product:
        logger.error(f"Не удалось обновить товар с ID {product_id}")
        bot.send_message(
            message.chat.id,
            "Ошибка при обновлении товара.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние PRODUCT_EDIT_MENU
    bot.set_state(message.from_user.id, BotStates.PRODUCT_EDIT_MENU, message.chat.id)
    
    # Сохраняем ID товара в данных состояния для возможности возврата через кнопку "Назад"
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['current_product_id'] = product_id
    
    # Отправляем сообщение об успешном обновлении
    keyboard = keyboards.get_product_edit_keyboard(product_id)
    
    # Формируем информацию о товаре
    category = db.get_category(updated_product.category_id)
    category_name = category.name if category else "Категория не найдена"
    availability = "В наличии ✅" if updated_product.available else "Отсутствует ❌"
    
    bot.send_message(
        message.chat.id,
        f"✅ Название товара успешно изменено!\n\n"
        f"Старое название: {old_name}\n"
        f"Новое название: {updated_product.name}\n\n"
        f"📋 Информация о товаре:\n\n"
        f"📦 Название: {updated_product.name}\n"
        f"🏷️ Категория: {category_name}\n"
        f"💰 Цена: {utils.format_money(updated_product.price)}/{updated_product.unit}\n"
        f"📊 Статус: {availability}\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )

def delete_product_select(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Выбор товара для удаления."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние PRODUCT_DELETE_SELECT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_DELETE_SELECT, call.message.chat.id)
    
    bot.edit_message_text(
        "Выберите категорию товара для удаления:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_categories_keyboard("delete_category_products")
    )

def show_products_for_delete(bot: telebot.TeleBot, call: types.CallbackQuery, category_id: int) -> None:
    """Показать список товаров категории для удаления."""
    logger = logging.getLogger(__name__)
    logger.info(f"Выбор товара для удаления в категории {category_id}")
    
    bot.answer_callback_query(call.id)
    
    # Получаем категорию
    category = db.get_category(category_id)
    if not category:
        logger.error(f"Категория не найдена: {category_id}")
        bot.edit_message_text(
            "Категория не найдена",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем все товары в категории
    products = db.get_products(category_id)
    if not products:
        bot.edit_message_text(
            f"В категории '{category.name}' нет товаров.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_categories_keyboard("delete_category_products")
        )
        return
    
    # Создаем клавиатуру с товарами
    keyboard = types.InlineKeyboardMarkup()
    for product in products:
        status = "✅" if product.available else "❌"
        keyboard.add(types.InlineKeyboardButton(
            f"{product.name} [{status}]", 
            callback_data=f"delete_product_{product.id}"
        ))
    
    # Добавляем кнопку "Назад"
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Товары в категории '{category.name}'.\nВыберите товар для удаления:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def delete_product_confirm(bot: telebot.TeleBot, call: types.CallbackQuery, product_id: int) -> None:
    """Подтверждение удаления товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Создаем клавиатуру для подтверждения удаления
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Кнопки "Да" и "Нет"
    keyboard.add(
        types.InlineKeyboardButton("Да", callback_data=f"confirm_delete_product_{product_id}"),
        types.InlineKeyboardButton("Нет", callback_data="cancel_delete_product")
    )
    
    # Запрашиваем подтверждение
    bot.edit_message_text(
        f"Вы уверены, что хотите удалить товар '{product.name}'?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def delete_product_execute(bot: telebot.TeleBot, call: types.CallbackQuery, product_id: int) -> None:
    """Удаление товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем товар для отображения информации
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Запоминаем информацию о товаре перед удалением
    product_name = product.name
    category_id = product.category_id
    category = db.get_category(category_id)
    category_name = category.name if category else "Неизвестная категория"
    
    # Удаляем товар
    if db.delete_product(product_id):
        # Устанавливаем состояние ADMIN_MODE
        bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
        
        bot.edit_message_text(
            f"✅ Товар '{product_name}' из категории '{category_name}' успешно удален!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
    else:
        bot.edit_message_text(
            f"❌ Ошибка при удалении товара '{product_name}'.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def save_data(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Сохранение всех данных."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    try:
        # Сначала сохраняем текущие данные
        db.save_all()
        
        # Затем создаем резервную копию
        backup_path = db.backup_data()
        backup_name = os.path.basename(backup_path)
        
        bot.edit_message_text(
            f"✅ Данные успешно сохранены!\n\n"
            f"Создана резервная копия: {backup_name}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        logger.info(f"Данные успешно сохранены пользователем {call.from_user.id}, создана копия: {backup_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {str(e)}")
        bot.edit_message_text(
            f"❌ Произошла ошибка при сохранении данных: {str(e)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def load_data_list(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показывает список доступных резервных копий данных."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние BACKUP_SELECT
    bot.set_state(call.from_user.id, BotStates.BACKUP_SELECT, call.message.chat.id)
    
    try:
        # Проверяем и создаем директорию для резервных копий, если она не существует
        os.makedirs(config.BACKUP_DIR, exist_ok=True)
        
        # Получаем список доступных резервных копий
        backups = db.list_backups()
        
        if not backups:
            bot.edit_message_text(
                f"Нет доступных резервных копий данных.\n\n"
                f"Директория для резервных копий: {config.BACKUP_DIR}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_admin_main_keyboard()
            )
            return
        
        # Создаем клавиатуру с резервными копиями
        keyboard = types.InlineKeyboardMarkup()
        
        for backup in backups:
            keyboard.add(types.InlineKeyboardButton(
                f"Копия от {backup}", 
                callback_data=f"load_backup_{backup}"
            ))
        
        # Добавляем кнопку "Назад"
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.edit_message_text(
            f"Выберите резервную копию для загрузки:\n"
            f"Всего копий: {len(backups)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке списка резервных копий: {str(e)}")
        bot.edit_message_text(
            f"❌ Произошла ошибка при загрузке списка резервных копий: {str(e)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def load_backup(bot: telebot.TeleBot, call: types.CallbackQuery, backup_name: str) -> None:
    """Загрузка выбранной резервной копии данных."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    try:
        # Формируем путь к резервной копии
        backup_path = os.path.join(config.BACKUP_DIR, backup_name)
        
        # Проверяем наличие директории резервной копии
        if not os.path.exists(backup_path):
            logger.error(f"Резервная копия не найдена: {backup_path}")
            bot.edit_message_text(
                "❌ Выбранная резервная копия не найдена.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_admin_main_keyboard()
            )
            return
        
        # Загружаем данные из резервной копии
        if db.restore_data(backup_path):
            bot.edit_message_text(
                f"✅ Данные успешно загружены из резервной копии от {backup_name}!",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_admin_main_keyboard()
            )
            logger.info(f"Данные успешно загружены из резервной копии {backup_name} пользователем {call.from_user.id}")
        else:
            bot.edit_message_text(
                "❌ Произошла ошибка при загрузке данных из резервной копии.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_admin_main_keyboard()
            )
            logger.error(f"Ошибка при загрузке данных из резервной копии {backup_name}")
    except Exception as e:
        logger.error(f"Ошибка при загрузке резервной копии: {str(e)}")
        bot.edit_message_text(
            f"❌ Произошла ошибка при загрузке резервной копии: {str(e)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def show_analytics(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показывает аналитику по продажам и клиентам."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние ANALYTICS_VIEW
    bot.set_state(call.from_user.id, BotStates.ANALYTICS_VIEW, call.message.chat.id)
    
    try:
        # Получаем аналитические данные
        top_customers_by_amount = get_top_customers(by_amount=True, limit=5)
        top_customers_by_frequency = get_top_customers(by_amount=False, limit=5)
        
        # Получаем популярные товары за разные периоды
        popular_week = get_popular_products(days=7, limit=3)
        popular_month = get_popular_products(days=30, limit=3)
        popular_3months = get_popular_products(days=90, limit=3)
        popular_year = get_popular_products(days=365, limit=3)
        
        # Текущая дата для отображения в аналитике
        current_date = utils.format_date(datetime.now().isoformat())
        
        # Формируем текст с аналитикой
        analytics_text = f"📊 *Аналитика магазина*\nДата: {current_date}\n\n"
        
        # Топ клиентов по сумме заказов
        analytics_text += "*🏆 Топ клиентов по сумме заказов:*\n"
        if top_customers_by_amount:
            for i, (user_id, name, total) in enumerate(top_customers_by_amount, 1):
                analytics_text += f"{i}. {name}: {utils.format_money(total)}\n"
        else:
            analytics_text += "Нет данных\n"
        
        analytics_text += "\n*🔄 Топ клиентов по частоте заказов:*\n"
        if top_customers_by_frequency:
            for i, (user_id, name, count) in enumerate(top_customers_by_frequency, 1):
                analytics_text += f"{i}. {name}: {count} заказов\n"
        else:
            analytics_text += "Нет данных\n"
        
        # Популярные товары
        analytics_text += "\n*📦 Популярные товары за неделю:*\n"
        if popular_week:
            for i, (product_id, name, count) in enumerate(popular_week, 1):
                analytics_text += f"{i}. {name}: {count} раз\n"
        else:
            analytics_text += "Нет данных\n"
        
        analytics_text += "\n*📦 Популярные товары за месяц:*\n"
        if popular_month:
            for i, (product_id, name, count) in enumerate(popular_month, 1):
                analytics_text += f"{i}. {name}: {count} раз\n"
        else:
            analytics_text += "Нет данных\n"
        
        analytics_text += "\n*📦 Популярные товары за 3 месяца:*\n"
        if popular_3months:
            for i, (product_id, name, count) in enumerate(popular_3months, 1):
                analytics_text += f"{i}. {name}: {count} раз\n"
        else:
            analytics_text += "Нет данных\n"
        
        analytics_text += "\n*📦 Популярные товары за год:*\n"
        if popular_year:
            for i, (product_id, name, count) in enumerate(popular_year, 1):
                analytics_text += f"{i}. {name}: {count} раз\n"
        else:
            analytics_text += "Нет данных\n"
        
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        # Отправляем сообщение с аналитикой
        bot.edit_message_text(
            analytics_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при формировании аналитики: {str(e)}")
        bot.edit_message_text(
            f"❌ Произошла ошибка при формировании аналитики: {str(e)}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )

def get_top_customers(by_amount: bool = True, limit: int = 5) -> list:
    """
    Получает список самых активных клиентов.
    
    Args:
        by_amount: True - сортировка по сумме заказов, False - по количеству заказов
        limit: максимальное количество клиентов в списке
        
    Returns:
        Список кортежей (user_id, name, total/count)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем все заказы
        orders = db.get_all_orders()
        
        # Словарь для хранения статистики по клиентам
        customer_stats = {}
        
        for order in orders:
            try:
                user_id = order.user_id
                if not user_id:
                    continue
                    
                user = db.get_user(user_id)
                
                if not user:
                    continue
                    
                # Формируем имя пользователя
                name = "Пользователь"
                if hasattr(user, 'first_name') and user.first_name:
                    name = user.first_name
                    if hasattr(user, 'last_name') and user.last_name:
                        name += f" {user.last_name}"
                
                if user_id not in customer_stats:
                    customer_stats[user_id] = {
                        'name': name,
                        'total': 0,
                        'count': 0
                    }
                
                # Обновляем статистику
                order_total = getattr(order, 'total', 0)
                customer_stats[user_id]['total'] += order_total
                customer_stats[user_id]['count'] += 1
            except Exception as e:
                logger.error(f"Ошибка при обработке заказа {order.id}: {str(e)}")
                continue
        
        # Сортируем клиентов
        if by_amount:
            # По сумме заказов
            sorted_customers = sorted(
                [(user_id, stats['name'], stats['total']) for user_id, stats in customer_stats.items()],
                key=lambda x: x[2],
                reverse=True
            )
        else:
            # По количеству заказов
            sorted_customers = sorted(
                [(user_id, stats['name'], stats['count']) for user_id, stats in customer_stats.items()],
                key=lambda x: x[2],
                reverse=True
            )
        
        # Возвращаем ограниченный список
        return sorted_customers[:limit]
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка активных клиентов: {str(e)}")
        return []

def get_popular_products(days: int = 30, limit: int = 5) -> list:
    """
    Получает список самых популярных товаров за указанный период.
    
    Args:
        days: количество дней для анализа
        limit: максимальное количество товаров в списке
        
    Returns:
        Список кортежей (product_id, name, count)
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем все заказы
        all_orders = db.get_all_orders()
        
        # Фильтруем заказы по дате
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Словарь для хранения статистики по товарам
        product_stats = {}
        
        for order in all_orders:
            # Проверяем дату заказа
            try:
                order_date = datetime.fromisoformat(order.created_at)
                if order_date < cutoff_date:
                    continue
            except (ValueError, TypeError):
                logger.warning(f"Неверный формат даты в заказе {order.id}: {order.created_at}")
                continue
                
            # Подсчитываем товары в заказе
            for item in order.items:
                try:
                    product_id = item.product_id
                    quantity = getattr(item, 'quantity', 1)  # Используем 1, если атрибут quantity не найден
                except AttributeError:
                    # Если item - словарь, а не объект CartItem
                    if isinstance(item, dict):
                        product_id = item.get('product_id')
                        quantity = item.get('quantity', 1)
                    else:
                        logger.warning(f"Неверный формат товара в заказе {order.id}: {item}")
                        continue
                
                if not product_id:
                    continue
                    
                product = db.get_product(product_id)
                
                if not product:
                    continue
                    
                if product_id not in product_stats:
                    product_stats[product_id] = {
                        'name': product.name,
                        'count': 0
                    }
                
                # Обновляем статистику
                product_stats[product_id]['count'] += quantity
        
        # Сортируем товары по популярности
        sorted_products = sorted(
            [(product_id, stats['name'], stats['count']) for product_id, stats in product_stats.items()],
            key=lambda x: x[2],
            reverse=True
        )
        
        # Возвращаем ограниченный список
        return sorted_products[:limit]
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка популярных товаров: {str(e)}")
        return []

def edit_product_price_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало процесса изменения цены товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 4:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    product_id = int(data_parts[3])
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Сохраняем ID товара в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['edit_product_id'] = product_id
        data['current_product_id'] = product_id
    
    # Устанавливаем состояние PRODUCT_EDIT_PRICE_INPUT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_EDIT_PRICE_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        f"Текущая цена товара '{product.name}': {utils.format_money(product.price)}\n"
        f"Введите новую цену (в рублях, например: 99.90):",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def edit_product_price_save(bot: telebot.TeleBot, message: types.Message) -> None:
    """Сохранение новой цены товара."""
    logger = logging.getLogger(__name__)
    
    price_text = message.text.strip()
    
    try:
        # Пробуем преобразовать введенную цену в число с плавающей точкой
        price = float(price_text.replace(',', '.'))
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
    except ValueError:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Неверный формат цены. Пожалуйста, введите положительное число (например: 99.90):",
            reply_markup=keyboard
        )
        return
    
    # Получаем ID товара из данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        product_id = data.get('edit_product_id')
    
    if not product_id:
        logger.error("ID товара не найден в данных состояния")
        bot.send_message(
            message.chat.id,
            "Ошибка: ID товара не найден в данных состояния.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем старую цену товара для сообщения
    product = db.get_product(product_id)
    old_price = product.price if product else 0
    
    # Обновляем цену товара
    updated_product = db.update_product(product_id, price=price)
    
    if not updated_product:
        logger.error(f"Не удалось обновить товар с ID {product_id}")
        bot.send_message(
            message.chat.id,
            "Ошибка при обновлении товара.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние PRODUCT_EDIT_MENU
    bot.set_state(message.from_user.id, BotStates.PRODUCT_EDIT_MENU, message.chat.id)
    
    # Сохраняем ID товара в данных состояния для возможности возврата через кнопку "Назад"
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['current_product_id'] = product_id
    
    # Отправляем сообщение об успешном обновлении
    keyboard = keyboards.get_product_edit_keyboard(product_id)
    
    # Формируем информацию о товаре
    category = db.get_category(updated_product.category_id)
    category_name = category.name if category else "Категория не найдена"
    availability = "В наличии ✅" if updated_product.available else "Отсутствует ❌"
    
    bot.send_message(
        message.chat.id,
        f"✅ Цена товара успешно изменена!\n\n"
        f"Товар: {updated_product.name}\n"
        f"Старая цена: {utils.format_money(old_price)}\n"
        f"Новая цена: {utils.format_money(updated_product.price)}\n\n"
        f"📋 Информация о товаре:\n\n"
        f"📦 Название: {updated_product.name}\n"
        f"🏷️ Категория: {category_name}\n"
        f"💰 Цена: {utils.format_money(updated_product.price)}/{updated_product.unit}\n"
        f"📊 Статус: {availability}\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )

def edit_product_image_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало процесса изменения изображения товара."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 4:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    product_id = int(data_parts[3])
    
    # Получаем товар
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.edit_message_text(
            "Товар не найден",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Сохраняем ID товара в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['edit_product_id'] = product_id
        data['current_product_id'] = product_id
    
    # Устанавливаем состояние PRODUCT_EDIT_IMAGE_INPUT
    bot.set_state(call.from_user.id, BotStates.PRODUCT_EDIT_IMAGE_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    # Отправляем текущее изображение, если оно есть
    if product.image_path:
        try:
            # Сначала отправляем текущее изображение
            bot.send_photo(
                chat_id=call.message.chat.id,
                photo=product.image_path,
                caption=f"Текущее изображение товара '{product.name}'"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке изображения: {str(e)}")
    
    # Отправляем сообщение с запросом нового изображения
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Отправьте новое изображение для товара '{product.name}'.\n"
             f"Или нажмите 'Назад' для отмены.",
        reply_markup=keyboard
    )

def edit_product_image_upload(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка загрузки нового изображения товара при редактировании."""
    logger = logging.getLogger(__name__)
    
    # Получаем ID товара из данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        product_id = data.get('edit_product_id')
        if not product_id:
            product_id = data.get('current_product_id')
    
    if not product_id:
        logger.error("ID товара не найден в данных состояния")
        bot.send_message(
            message.chat.id,
            "Ошибка: ID товара не найден в данных состояния.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем товар для отображения информации
    product = db.get_product(product_id)
    if not product:
        logger.error(f"Товар не найден: {product_id}")
        bot.send_message(
            message.chat.id,
            "Товар не найден",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Получаем информацию о новом фото
    photo = message.photo[-1]  # Берем последнее (самое качественное) фото
    file_id = photo.file_id
    
    # Получаем старый file_id для информации
    old_image_path = product.image_path
    
    # Обновляем изображение товара
    updated_product = db.update_product(product_id, image_path=file_id)
    
    if not updated_product:
        logger.error(f"Не удалось обновить товар с ID {product_id}")
        bot.send_message(
            message.chat.id,
            "Ошибка при обновлении изображения товара.",
            reply_markup=keyboards.get_admin_main_keyboard()
        )
        return
    
    # Устанавливаем состояние PRODUCT_EDIT_MENU
    bot.set_state(message.from_user.id, BotStates.PRODUCT_EDIT_MENU, message.chat.id)
    
    # Сохраняем ID товара в данных состояния для возможности возврата через кнопку "Назад"
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['current_product_id'] = product_id
    
    # Отправляем сообщение об успешном обновлении
    keyboard = keyboards.get_product_edit_keyboard(product_id)
    
    # Формируем информацию о товаре
    category = db.get_category(updated_product.category_id)
    category_name = category.name if category else "Категория не найдена"
    availability = "В наличии ✅" if updated_product.available else "Отсутствует ❌"
    
    # Отправляем новое изображение с информацией об обновлении
    try:
        bot.send_photo(
            chat_id=message.chat.id,
            photo=file_id,
            caption=f"✅ Изображение товара успешно обновлено!\n\n"
                    f"📋 Информация о товаре:\n\n"
                    f"📦 Название: {updated_product.name}\n"
                    f"🏷️ Категория: {category_name}\n"
                    f"💰 Цена: {utils.format_money(updated_product.price)}/{updated_product.unit}\n"
                    f"📊 Статус: {availability}",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке фото: {str(e)}")
        # В случае ошибки отправляем обычное сообщение
        bot.send_message(
            message.chat.id,
            f"✅ Изображение товара успешно обновлено!\n\n"
            f"📋 Информация о товаре:\n\n"
            f"📦 Название: {updated_product.name}\n"
            f"🏷️ Категория: {category_name}\n"
            f"💰 Цена: {utils.format_money(updated_product.price)}/{updated_product.unit}\n"
            f"📊 Статус: {availability}\n\n"
            f"Выберите действие:",
            reply_markup=keyboard
        ) 