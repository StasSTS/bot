from typing import Dict, Any, Optional
import os
import telebot
from telebot import types
import logging
from types import SimpleNamespace

import keyboards
import utils
import config
from database import db
from states import BotStates

# Состояния для режима покупателя
(
    CATEGORY_VIEW,
    PRODUCT_VIEW,
    PRODUCT_DETAIL,
    FAVORITES_VIEW,
    SEARCH_INPUT,
    SEARCH_RESULTS
) = range(6)

def back_to_customer_main(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Вернуться в главное меню покупателя."""
    logger = logging.getLogger(__name__)
    logger.info(f"Возврат в главное меню покупателя: user_id={call.from_user.id}")
    
    try:
        bot.answer_callback_query(call.id)
        
        # Устанавливаем состояние CUSTOMER_MODE
        bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
        
        # Проверяем существование пользователя
        user_id = call.from_user.id
        user = db.get_user(user_id)
        
        if not user:
            logger.warning(f"Пользователь не найден при возврате в главное меню: user_id={user_id}")
            # Создаем простую клавиатуру
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("Режим покупателя", callback_data="mode_customer"))
            keyboard.add(types.InlineKeyboardButton("Администрирование", callback_data="mode_admin"))
            
            bot.edit_message_text(
                "Выберите режим работы:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
            return
        
        try:
            # Проверяем, есть ли у сообщения текст (если это фото с товаром, то может вызвать ошибку)
            if call.message.content_type == 'photo':
                # Если это фото, то удаляем его и отправляем новое сообщение
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="Главное меню покупателя",
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                )
            else:
                # Если это текстовое сообщение, то просто обновляем его
                bot.edit_message_text(
                    "Главное меню покупателя",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                )
        except Exception as e:
            # Если возникла ошибка при редактировании сообщения, пробуем отправить новое
            logger.error(f"Ошибка при обновлении сообщения: {str(e)}, пробуем отправить новое сообщение")
            try:
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="Главное меню покупателя",
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                )
            except Exception as e2:
                logger.error(f"Ошибка при отправке нового сообщения: {str(e2)}")
    except Exception as e:
        logger.error(f"Критическая ошибка в back_to_customer_main: {str(e)}")
        try:
            bot.send_message(
                chat_id=call.message.chat.id,
                text="Произошла ошибка. Пожалуйста, отправьте команду /start для перезапуска бота."
            )
        except:
            pass

def category_selected(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать товары в выбранной категории."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID категории из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 2:
        back_to_customer_main(bot, call)
        return
    
    category_id = int(data_parts[1])
    category = db.get_category(category_id)
    
    if not category:
        bot.edit_message_text(
            "Категория не найдена.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
        )
        return
    
    # Сохраняем ID категории в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['current_category_id'] = category_id
    
    # Устанавливаем состояние CATEGORY_VIEW
    bot.set_state(call.from_user.id, BotStates.CATEGORY_VIEW, call.message.chat.id)
    
    # Показываем товары в категории
    products = db.get_available_products(category_id)
    
    if not products:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.edit_message_text(
            f"В категории '{category.name}' нет доступных товаров.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
        return
    
    bot.edit_message_text(
        f"Товары в категории '{category.name}':",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_products_by_category_keyboard(category_id, call.from_user.id)
    )

def product_selected(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать детальную информацию о товаре."""
    # Безопасно отвечаем на callback, если это реально callback
    if hasattr(call, 'id') and call.id is not None:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 2:
        back_to_customer_main(bot, call)
        return
    
    product_id = int(data_parts[1])
    product = db.get_product(product_id)
    
    if not product or not product.available:
        bot.edit_message_text(
            "Товар не найден или недоступен.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
        )
        return
    
    # Сохраняем ID товара в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['current_product_id'] = product_id
    
    # Устанавливаем состояние PRODUCT_DETAIL
    bot.set_state(call.from_user.id, BotStates.PRODUCT_DETAIL, call.message.chat.id)
    
    # Формируем текст с информацией о товаре
    unit_text = "шт" if product.unit == "шт" else "кг"
    product_text = f"{product.name}\nЦена: {utils.format_money(product.price)}/{unit_text}"
    
    # Показываем детальную информацию о товаре
    if product.image_path:
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_photo(
                chat_id=call.message.chat.id,
                photo=product.image_path,
                caption=product_text,
                reply_markup=keyboards.get_product_detail_keyboard(product, call.from_user.id, allow_custom_quantity=True)
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка при отправке фото товара: {e}")
            bot.edit_message_text(
                product_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_product_detail_keyboard(product, call.from_user.id, allow_custom_quantity=True)
            )
    else:
        bot.edit_message_text(
            product_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_product_detail_keyboard(product, call.from_user.id, allow_custom_quantity=True)
        )

def back_to_category(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Вернуться к просмотру категории."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID категории из данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        category_id = data.get('current_category_id')
    
    if not category_id:
        back_to_customer_main(bot, call)
        return
    
    # Повторно загружаем категорию
    category = db.get_category(category_id)
    if not category:
        back_to_customer_main(bot, call)
        return
    
    # Устанавливаем состояние CATEGORY_VIEW
    bot.set_state(call.from_user.id, BotStates.CATEGORY_VIEW, call.message.chat.id)
    
    try:
        # Пытаемся удалить предыдущее сообщение с фото, если оно было
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    except Exception:
        pass  # Игнорируем ошибки при удалении
    
    # Создаем новое сообщение с товарами категории
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Товары в категории '{category.name}':",
        reply_markup=keyboards.get_products_by_category_keyboard(category_id, call.from_user.id)
    )

def add_to_favorites(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Добавить товар в избранное."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        return
    
    product_id = int(data_parts[2])
    user_id = call.from_user.id
    
    # Добавляем товар в избранное
    user = db.get_user(user_id)
    user.add_to_favorites(product_id)
    db.update_user(user_id, favorites=user.favorites)
    
    # Обновляем информацию о товаре
    product = db.get_product(product_id)
    
    if not product:
        back_to_customer_main(bot, call)
        return
    
    # Обновляем клавиатуру
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_product_detail_keyboard(product, user_id)
    )

def remove_from_favorites(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Удалить товар из избранного."""
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        return
    
    product_id = int(data_parts[2])
    user_id = call.from_user.id
    
    # Удаляем товар из избранного
    user = db.get_user(user_id)
    user.remove_from_favorites(product_id)
    db.update_user(user_id, favorites=user.favorites)
    
    # Обновляем информацию о товаре
    product = db.get_product(product_id)
    
    if not product:
        back_to_customer_main(bot, call)
        return
    
    # Обновляем клавиатуру
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_product_detail_keyboard(product, user_id)
    )

def view_favorites(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать избранные товары."""
    bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    favorites = db.get_favorite_products(user_id)
    
    # Устанавливаем состояние FAVORITES_VIEW
    bot.set_state(call.from_user.id, BotStates.FAVORITES_VIEW, call.message.chat.id)
    
    if not favorites:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.edit_message_text(
            "У вас нет избранных товаров.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
    else:
        bot.edit_message_text(
            "Ваши избранные товары:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_favorites_keyboard(user_id)
        )

def search_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начать поиск товаров."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние SEARCH_INPUT
    bot.set_state(call.from_user.id, BotStates.SEARCH_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        "Введите название товара для поиска:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def search_process(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработать поисковый запрос."""
    search_query = message.text.strip()
    
    if not search_query:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Введите название товара для поиска:",
            reply_markup=keyboard
        )
        return
    
    # Поиск товаров
    search_results = db.search_products(search_query)
    
    # Устанавливаем состояние SEARCH_RESULTS
    bot.set_state(message.from_user.id, BotStates.SEARCH_RESULTS, message.chat.id)
    
    if not search_results:
        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            f"По запросу '{search_query}' ничего не найдено.",
            reply_markup=keyboard
        )
    else:
        # Создаем клавиатуру с результатами поиска
        keyboard = types.InlineKeyboardMarkup()
        
        for product in sorted(search_results, key=lambda p: p.name):
            keyboard.add(types.InlineKeyboardButton(
                f"{product.name} - {utils.format_money(product.price)}",
                callback_data=f"product_{product.id}"
            ))
        
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            f"Результаты поиска по запросу '{search_query}':",
            reply_markup=keyboard
        )

def add_to_cart(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Добавить товар в корзину."""
    bot.answer_callback_query(call.id)
    
    # Получаем данные из callback_data
    data_parts = call.data.split("_")
    
    # Проверяем правильность формата callback_data
    if len(data_parts) < 5 or "_".join(data_parts[:3]) != "add_to_cart":
        logger = logging.getLogger(__name__)
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    try:
        product_id = int(data_parts[3])
        quantity = float(data_parts[4])
    except (ValueError, IndexError):
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при обработке данных из callback_data: {call.data}")
        return
    
    user_id = call.from_user.id
    
    # Добавляем товар в корзину
    user = db.get_user(user_id)
    user.add_to_cart(product_id, quantity)
    db.update_user(user_id)
    
    # Обновляем информацию о товаре
    product = db.get_product(product_id)
    
    if not product:
        back_to_customer_main(bot, call)
        return
    
    # Обновляем клавиатуру
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_product_detail_keyboard(product, user_id, allow_custom_quantity=True)
    )
    
    # Показываем сообщение о добавлении в корзину
    bot.answer_callback_query(
        call.id,
        text=f"Товар '{product.name}' добавлен в корзину"
    )

def remove_from_cart(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Удалить товар из корзины."""
    logger = logging.getLogger(__name__)
    logger.info(f"Удаление товара из корзины: user_id={call.from_user.id}, callback_data={call.data}")
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID товара из callback_data
    data_parts = call.data.split("_")
    
    # Проверяем правильность формата callback_data
    if len(data_parts) < 4 or "_".join(data_parts[:3]) != "remove_from_cart":
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    try:
        product_id = int(data_parts[3])
    except (ValueError, IndexError):
        logger.error(f"Ошибка при обработке данных из callback_data: {call.data}")
        return
    
    user_id = call.from_user.id
    
    # Получаем информацию о товаре
    product = db.get_product(product_id)
    
    if not product:
        logger.error(f"Товар не найден: product_id={product_id}")
        back_to_customer_main(bot, call)
        return
    
    # Проверяем, есть ли товар в корзине
    user = db.get_user(user_id)
    
    # Находим товар в корзине
    cart_item = next((item for item in user.cart if item.product_id == product_id), None)
    
    if not cart_item:
        # Товара нет в корзине
        logger.info(f"Товар {product_id} не найден в корзине пользователя {user_id}")
        bot.answer_callback_query(
            call.id,
            text="Этого товара нет в корзине"
        )
        return
    
    # Получаем количество в корзине для информационного сообщения
    quantity = cart_item.quantity
    
    # Удаляем товар из корзины полностью
    # Используем новый метод remove_cart_item вместо прямого изменения списка
    removed = user.remove_cart_item(product_id)
    
    if removed:
        # Сохраняем изменения
        db.update_user(user_id)
        logger.info(f"Товар {product_id} удален из корзины пользователя {user_id}")
        
        # Обновляем клавиатуру
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_product_detail_keyboard(product, user_id, allow_custom_quantity=True)
        )
        
        # Показываем сообщение об удалении из корзины
        unit_text = "шт" if product.unit == "шт" else "кг"
        bot.answer_callback_query(
            call.id,
            text=f"Товар '{product.name}' ({quantity} {unit_text}) удален из корзины"
        )
    else:
        logger.warning(f"Не удалось удалить товар {product_id} из корзины пользователя {user_id}")
        bot.answer_callback_query(
            call.id,
            text="Не удалось удалить товар из корзины"
        )

# Новая функция: обработка перехода к ручному вводу количества
def ask_custom_quantity(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Запросить у пользователя ввод количества товара вручную."""
    bot.answer_callback_query(call.id)
    # Сохраняем ID товара в состоянии
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        return
    product_id = int(data_parts[2])
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['current_product_id'] = product_id
    # Устанавливаем специальное состояние
    bot.set_state(call.from_user.id, BotStates.CUSTOM_QUANTITY_INPUT, call.message.chat.id)
    # Показываем ForceReply с подсказкой
    force_reply = types.ForceReply(selective=True, input_field_placeholder="Можете указать кол-во товара (например: 2.3)")
    bot.send_message(
        call.message.chat.id,
        "Введите нужное количество товара (например: 2.3):",
        reply_markup=force_reply
    )

# Новая функция: обработка ручного ввода количества
def process_custom_quantity(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка ручного ввода количества товара пользователем."""
    import re
    from database import db
    from states import BotStates
    user_id = message.from_user.id
    text = message.text.strip().replace(",", ".")
    # Проверяем, что введено число
    match = re.match(r"^\d+(\.\d+)?$", text)
    if not match:
        force_reply = types.ForceReply(selective=True, input_field_placeholder="Можете указать кол-во товара (например: 2.3)")
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректное число (например: 2.3):",
            reply_markup=force_reply
        )
        return
    quantity = float(text)
    if quantity <= 0:
        force_reply = types.ForceReply(selective=True, input_field_placeholder="Можете указать кол-во товара (например: 2.3)")
        bot.send_message(
            message.chat.id,
            "Количество должно быть больше 0. Попробуйте ещё раз:",
            reply_markup=force_reply
        )
        return
    # Получаем ID товара из состояния
    with bot.retrieve_data(user_id, message.chat.id) as data:
        product_id = data.get('current_product_id')
    if not product_id:
        bot.send_message(message.chat.id, "Ошибка: не удалось определить товар.")
        return
    # Добавляем товар в корзину
    user = db.get_user(user_id)
    user.add_to_cart(product_id, quantity)
    db.update_user(user_id)
    product = db.get_product(product_id)
    # Сбрасываем состояние
    bot.set_state(user_id, BotStates.PRODUCT_DETAIL, message.chat.id)
    # Показываем подтверждение и обновляем детали товара
    bot.send_message(
        message.chat.id,
        f"Товар '{product.name}' ({quantity} {product.unit}) добавлен в корзину!"
    )
    call_product_selected_from_message(bot, message, product_id)

def call_product_selected_from_message(bot, message, product_id):
    """Вызывает product_selected с эмуляцией CallbackQuery на основе Message."""
    class FakeFromUser:
        def __init__(self, id):
            self.id = id
    class FakeMessage:
        def __init__(self, chat_id, message_id, content_type):
            class Chat:
                def __init__(self, id):
                    self.id = id
            self.chat = Chat(chat_id)
            self.message_id = message_id
            self.content_type = content_type
    class FakeCall:
        def __init__(self, user_id, chat_id, message_id, content_type, data):
            self.from_user = FakeFromUser(user_id)
            self.message = FakeMessage(chat_id, message_id, content_type)
            self.data = data
        def answer(self):
            pass
        def answer_callback_query(self, *args, **kwargs):
            pass
        id = 0
    fake_call = FakeCall(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=getattr(message, 'message_id', None),
        content_type=getattr(message, 'content_type', 'text'),
        data=f"product_{product_id}"
    )
    product_selected(bot, fake_call) 