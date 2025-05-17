from typing import Dict, Any, Optional
import telebot
from telebot import types
import logging
import re

import config
import keyboards
import utils
from database import db
from states import BotStates

# Состояния для корзины
(
    CART_VIEW,
    CHECKOUT_START,
    PHONE_INPUT,
    ADDRESS_INPUT,
    DELIVERY_TIME_SELECT,
    ORDER_CONFIRMATION
) = range(6)

def view_cart(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Просмотр корзины."""
    logger = logging.getLogger(__name__)
    logger.info(f"Вызов функции view_cart для пользователя: {call.from_user.id}")
    
    try:
        bot.answer_callback_query(call.id)
        
        user_id = call.from_user.id
        
        # Проверяем существование пользователя и корзины
        user = db.get_user(user_id)
        if not user:
            logger.error(f"Пользователь не найден: {user_id}")
            try:
                bot.edit_message_text(
                    "Произошла ошибка при загрузке корзины. Попробуйте позже.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
                )
            except Exception as e2:
                logger.error(f"Не удалось обновить сообщение после ошибки: {str(e2)}")
                try:
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text="Произошла ошибка. Пожалуйста, используйте /start для перезапуска бота."
                    )
                except:
                    pass
            return
        
        # Устанавливаем состояние CART_VIEW
        try:
            bot.set_state(call.from_user.id, BotStates.CART_VIEW, call.message.chat.id)
        except Exception as e:
            logger.error(f"Не удалось установить состояние: {str(e)}")
        
        # Получаем содержимое корзины
        if not user.cart:
            # Обрабатываем пустую корзину
            logger.info(f"Корзина пользователя {user_id} пуста")
            try:
                bot.edit_message_text(
                    "Ваша корзина пуста.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
                )
            except Exception as e2:
                logger.error(f"Не удалось обновить сообщение с пустой корзиной: {str(e2)}")
                try:
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text="Ваша корзина пуста.",
                        reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
                    )
                except:
                    pass
            return
        
        # Получаем детали корзины и общую сумму
        try:
            cart_text, total = utils.get_cart_details(user_id)
            logger.info(f"Получены детали корзины для {user_id}: {total} руб.")
            
            # Проверяем тип сообщения
            if hasattr(call.message, 'content_type') and call.message.content_type == 'photo':
                # Если это фото, то удаляем его и отправляем новое сообщение
                logger.info("Удаляем фото и отправляем текст")
                try:
                    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text=f"Ваша корзина:\n\n{cart_text}\n\nИтого: {utils.format_money(total)}",
                        reply_markup=keyboards.get_cart_keyboard(user_id)
                    )
                except Exception as e3:
                    logger.error(f"Ошибка при удалении фото: {str(e3)}")
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text=f"Ваша корзина:\n\n{cart_text}\n\nИтого: {utils.format_money(total)}",
                        reply_markup=keyboards.get_cart_keyboard(user_id)
                    )
            else:
                # Если это текст, редактируем сообщение
                logger.info("Редактируем текущее сообщение")
                bot.edit_message_text(
                    f"Ваша корзина:\n\n{cart_text}\n\nИтого: {utils.format_money(total)}",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_cart_keyboard(user_id)
                )
        except Exception as e:
            logger.error(f"Ошибка при отображении корзины: {str(e)}")
            try:
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="Не удалось загрузить корзину. Пожалуйста, используйте /start для перезапуска бота."
                )
            except:
                pass
            
    except Exception as e:
        logger.error(f"Критическая ошибка при просмотре корзины: {str(e)}")
        try:
            bot.edit_message_text(
                "Произошла ошибка при загрузке корзины. Попробуйте позже.",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
            )
        except Exception as e2:
            logger.error(f"Не удалось обновить сообщение после критической ошибки: {str(e2)}")
            try:
                bot.send_message(
                    chat_id=call.message.chat.id,
                    text="Произошла ошибка. Пожалуйста, используйте /start для перезапуска бота."
                )
            except:
                pass

def clear_cart(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Очистить корзину."""
    bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    
    # Очищаем корзину
    user = db.get_user(user_id)
    user.clear_cart()
    db.update_user(user_id)
    
    # Возвращаемся в главное меню
    bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
    
    bot.edit_message_text(
        "Корзина очищена.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
    )

def checkout_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Начало оформления заказа."""
    bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    user = db.get_user(user_id)
    
    # Проверяем, не пуста ли корзина
    if not user.cart:
        bot.edit_message_text(
            "Ваша корзина пуста.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
        )
        return
    
    # Устанавливаем состояние CHECKOUT_START
    bot.set_state(call.from_user.id, BotStates.CHECKOUT_START, call.message.chat.id)
    
    # Показываем клавиатуру для оформления заказа
    bot.edit_message_text(
        "Для оформления заказа нам нужны ваши контактные данные.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_checkout_keyboard(user_id)
    )

def phone_input_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Запрос номера телефона."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние PHONE_INPUT
    bot.set_state(call.from_user.id, BotStates.PHONE_INPUT, call.message.chat.id)
    
    # Инициализируем пустой номер телефона в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['phone_digits'] = ""
    
    # Отображаем маску ввода и виртуальную клавиатуру
    update_phone_input_ui(bot, call.message, "")

def update_phone_input_ui(bot: telebot.TeleBot, message: types.Message, digits: str) -> None:
    """Обновляет интерфейс ввода телефона с текущими введенными цифрами
    
    Args:
        bot: Экземпляр бота
        message: Сообщение, которое нужно обновить
        digits: Текущие введенные цифры
    """
    # Форматируем телефон с маской
    masked_phone = utils.format_phone_with_mask(digits)
    
    text = (
        "Введите номер телефона:\n\n"
        f"📱 <b>+7 {masked_phone}</b>\n\n"
        "Используйте виртуальную клавиатуру ниже или введите номер с клавиатуры (10 цифр без кода страны)."
    )
    
    try:
        # Пытаемся обновить текст сообщения с клавиатурой
        bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=keyboards.get_phone_input_keyboard(digits),
            parse_mode='HTML'
        )
    except Exception as e:
        # Если не получилось обновить, логируем ошибку
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при обновлении интерфейса ввода телефона: {str(e)}")

def process_phone_digit(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обрабатывает нажатие на цифру виртуальной клавиатуры телефона"""
    # Сразу отправляем быстрый ответ на callback, чтобы телеграм не ждал
    bot.answer_callback_query(call.id)
    
    # Извлекаем цифру из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) != 3:
        return
    
    digit = data_parts[2]
    
    # Получаем текущие цифры из данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        current_digits = data.get('phone_digits', "")
        
        # Добавляем новую цифру, если еще не набрали 10
        if len(current_digits) < 10:
            current_digits += digit
            data['phone_digits'] = current_digits
    
    # Обновляем интерфейс
    update_phone_input_ui(bot, call.message, current_digits)

def process_phone_delete(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обрабатывает нажатие на кнопку удаления последней цифры"""
    # Сразу отправляем быстрый ответ на callback, чтобы телеграм не ждал
    bot.answer_callback_query(call.id)
    
    # Получаем текущие цифры из данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        current_digits = data.get('phone_digits', "")
        
        # Удаляем последнюю цифру, если они есть
        if current_digits:
            current_digits = current_digits[:-1]
            data['phone_digits'] = current_digits
    
    # Обновляем интерфейс
    update_phone_input_ui(bot, call.message, current_digits)

def process_phone_submit(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обрабатывает подтверждение введенного номера телефона"""
    bot.answer_callback_query(call.id)
    
    # Получаем текущие цифры из данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        digits = data.get('phone_digits', "")
    
    # Проверяем, что введено ровно 10 цифр
    if len(digits) != 10:
        bot.answer_callback_query(
            call.id,
            "Номер телефона должен содержать 10 цифр. Пожалуйста, введите корректный номер.",
            show_alert=True
        )
        return
    
    # Форматируем телефон
    formatted_phone = utils.format_phone("7" + digits)
    
    # Сохраняем телефон в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['phone'] = formatted_phone
        # Очищаем временные данные
        data.pop('phone_digits', None)
    
    # Сохраняем телефон в профиле пользователя
    user_id = call.from_user.id
    user = db.get_user(user_id)
    user.phone = formatted_phone
    db.update_user(user_id)
    
    # Устанавливаем состояние ADDRESS_INPUT
    bot.set_state(call.from_user.id, BotStates.ADDRESS_INPUT, call.message.chat.id)
    
    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    # Удаляем предыдущее сообщение с виртуальной клавиатурой
    try:
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при удалении сообщения с клавиатурой: {str(e)}")
    
    # Создаем форсированный ответ с подсказкой
    force_reply = types.ForceReply(selective=True, input_field_placeholder="Введите адрес доставки")
    
    # Отправляем новое сообщение с запросом адреса и подсказкой
    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Телефон сохранен: {formatted_phone}\n\n"
             f"Введите адрес доставки (укажите населенный пункт, улицу, дом, подъезд и квартиру):",
        reply_markup=force_reply
    )
    
    # Отправляем дополнительное сообщение с кнопкой "Назад"
    bot.send_message(
        chat_id=call.message.chat.id,
        text="Для возврата к предыдущему шагу нажмите кнопку ниже:",
        reply_markup=keyboard
    )

def use_saved_data(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Использовать сохраненные данные для заказа."""
    bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    user = db.get_user(user_id)
    
    # Проверяем, есть ли сохраненные данные
    if not user.phone or not user.address:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.edit_message_text(
            "У вас нет сохраненных данных.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard
        )
        return
    
    # Сохраняем данные в состоянии для последующих шагов
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['phone'] = user.phone
        data['address'] = user.address
    
    # Создаем заказ сразу без выбора времени доставки
    order = db.create_order(user_id, user.phone, user.address, None)
    
    if not order:
        bot.edit_message_text(
            "Ошибка при создании заказа.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
        )
        return
    
    # Отправляем уведомление администратору о новом заказе
    try:
        utils.notify_admin_about_new_order(bot, order.id)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Не удалось отправить уведомление администратору: {str(e)}")
        # Не прерываем основной процесс заказа
    
    # Устанавливаем состояние CUSTOMER_MODE
    bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
    
    # Подтверждаем заказ
    bot.edit_message_text(
        f"Заказ №{order.id} успешно оформлен!\n\n"
        f"Телефон: {order.phone}\n"
        f"Адрес доставки: {order.address}\n\n"
        f"Мы свяжемся с вами в ближайшее время для подтверждения заказа.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
    )

def process_phone(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка ввода номера телефона с клавиатуры."""
    phone = message.text.strip()
    
    # Проверка на количество цифр в номере
    digits = re.sub(r'\D', '', phone)
    
    # Если номер начинается с 8 или 7, не учитываем эту цифру при подсчете
    if digits.startswith('8') or digits.startswith('7'):
        digits = digits[1:]
    
    # Проверяем, что в номере не более 10 цифр
    if len(digits) > 10:
        # Обновляем виртуальную клавиатуру с сообщением об ошибке
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            current_digits = data.get('phone_digits', "")
        
        # Отправляем сообщение об ошибке
        bot.send_message(
            message.chat.id,
            "Номер телефона должен содержать не более 10 цифр (без учета кода страны).",
            reply_markup=keyboards.get_phone_input_keyboard(current_digits)
        )
        return
    
    # Если введено меньше 10 цифр, просто обновляем интерфейс
    if len(digits) < 10:
        # Сохраняем введенные цифры
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['phone_digits'] = digits
        
        # Обновляем интерфейс
        update_phone_input_ui(bot, message, digits)
        return
    
    # Форматируем телефон
    formatted_phone = utils.format_phone("7" + digits)
    
    # Сохраняем телефон в данных состояния
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['phone'] = formatted_phone
        # Очищаем временные данные
        data.pop('phone_digits', None)
    
    # Сохраняем телефон в профиле пользователя
    user_id = message.from_user.id
    user = db.get_user(user_id)
    user.phone = formatted_phone
    db.update_user(user_id)
    
    # Устанавливаем состояние ADDRESS_INPUT
    bot.set_state(message.from_user.id, BotStates.ADDRESS_INPUT, message.chat.id)
    
    # Запрашиваем адрес
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(keyboards.BACK_BUTTON)
    
    bot.send_message(
        message.chat.id,
        f"Телефон сохранен: {formatted_phone}\n\n"
        "Введите адрес доставки (укажите населенный пункт, улицу, дом, подъезд и квартиру):",
        reply_markup=keyboard
    )

def process_address(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработка введенного адреса."""
    address = message.text.strip()
    
    # Проверяем, что адрес не пустой
    if not address:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
        
        bot.send_message(
            message.chat.id,
            "Адрес не может быть пустым. Пожалуйста, введите адрес:",
            reply_markup=keyboard
        )
        return
    
    # Сохраняем адрес в данных состояния
    user_id = message.from_user.id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['address'] = address
        phone = data.get('phone', None)
    
    # Сохраняем в профиле пользователя
    user = db.get_user(user_id)
    user.address = address
    db.update_user(user_id)

    # Создаем заказ сразу без выбора времени доставки
    order = db.create_order(user_id, phone, address, None)
    
    if not order:
        bot.send_message(
            message.chat.id,
            "Ошибка при создании заказа.",
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
        )
        return
    
    # Отправляем уведомление администратору о новом заказе
    try:
        utils.notify_admin_about_new_order(bot, order.id)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Не удалось отправить уведомление администратору: {str(e)}")
        # Не прерываем основной процесс заказа
    
    # Устанавливаем состояние CUSTOMER_MODE
    bot.set_state(message.from_user.id, BotStates.CUSTOMER_MODE, message.chat.id)
    
    # Подтверждаем заказ
    bot.send_message(
        message.chat.id,
        f"Заказ №{order.id} успешно оформлен!\n\n"
        f"Телефон: {order.phone}\n"
        f"Адрес доставки: {order.address}\n\n"
        f"Мы свяжемся с вами в ближайшее время для подтверждения заказа.",
        reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
    )

def delivery_time_selected(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка выбора времени доставки."""
    bot.answer_callback_query(call.id)
    
    # Получаем выбранное время из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        return
    
    time_range = data_parts[2].replace("-", " - ")
    delivery_time = f"{time_range}:00"
    
    user_id = call.from_user.id
    
    # Получаем сохраненные данные для заказа
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        phone = data.get('phone', None)
        address = data.get('address', None)
    
    # Создаем заказ
    order = db.create_order(user_id, phone, address, delivery_time)
    
    if not order:
        bot.edit_message_text(
            "Ошибка при создании заказа.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
        )
        return
    
    # Отправляем уведомление администратору о новом заказе
    try:
        utils.notify_admin_about_new_order(bot, order.id)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Не удалось отправить уведомление администратору: {str(e)}")
        # Не прерываем основной процесс заказа
    
    # Устанавливаем состояние CUSTOMER_MODE
    bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
    
    # Подтверждаем заказ
    bot.edit_message_text(
        f"Заказ №{order.id} успешно оформлен!\n\n"
        f"Телефон: {order.phone}\n"
        f"Адрес доставки: {order.address}\n"
        f"Время доставки: {order.delivery_time}\n\n"
        f"Мы свяжемся с вами в ближайшее время для подтверждения заказа.",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
    ) 