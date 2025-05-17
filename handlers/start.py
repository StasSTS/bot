from typing import Dict, Any
import telebot
from telebot import types
import logging

import keyboards
import utils
from database import db
from states import BotStates
import config

# Константы для состояний
START, CUSTOMER_MODE, ADMIN_MODE = range(3)

def start_command(bot: telebot.TeleBot, message: types.Message) -> None:
    """Обработчик команды /start."""
    utils.update_user_data(message)
    
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id == config.ADMIN_USER_ID:
        # Устанавливаем статус админа в базе
        user = db.get_user(user_id)
        db.update_user(user_id, is_admin=True)
        
        # Отправляем приветственное сообщение с кнопками выбора режима
        bot.set_state(message.from_user.id, BotStates.START, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Добро пожаловать в магазин продуктов!\n"
            "Выберите режим работы:",
            reply_markup=keyboards.get_start_keyboard(user_id)
        )
    else:
        # Для обычных пользователей сразу показываем режим покупателя
        bot.set_state(message.from_user.id, BotStates.CUSTOMER_MODE, message.chat.id)
        bot.send_message(
            message.chat.id,
            "Заказ и доставка Овощей, Фруктов, Полуфабрикатов!",
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(user_id)
        )

def mode_selector(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработчик выбора режима."""
    logger = logging.getLogger(__name__)
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    if call.data == "mode_customer":
        # Устанавливаем состояние CUSTOMER_MODE
        bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы вошли в режим покупателя.",
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
        )
    
    elif call.data == "mode_admin":
        # Проверяем, имеет ли пользователь права администратора
        if user_id == config.ADMIN_USER_ID:
            logger.info(f"Пользователь {user_id} вошел в режим администратора (авторизован)")
            
            # Устанавливаем статус админа в базе
            user = db.get_user(user_id)
            db.update_user(user_id, is_admin=True)
            
            # Устанавливаем состояние ADMIN_MODE
            bot.set_state(call.from_user.id, BotStates.ADMIN_MODE, call.message.chat.id)
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Вы вошли в режим администратора.",
                reply_markup=keyboards.get_admin_main_keyboard()
            )
        else:
            # Если пользователь не имеет прав администратора, перенаправляем в режим покупателя
            logger.warning(f"Попытка неавторизованного доступа к админ-панели: user_id={user_id}")
            
            # Устанавливаем состояние CUSTOMER_MODE
            bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="У вас нет прав доступа к режиму администратора. Вы перенаправлены в режим покупателя.",
                reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
            )

def back_to_start(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработчик возврата к стартовому меню."""
    bot.answer_callback_query(call.id)
    
    user_id = call.from_user.id
    
    # Проверяем, является ли пользователь администратором
    if user_id == config.ADMIN_USER_ID:
        # Устанавливаем состояние START
        bot.set_state(call.from_user.id, BotStates.START, call.message.chat.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Выберите режим работы:",
            reply_markup=keyboards.get_start_keyboard(user_id)
        )
    else:
        # Для обычных пользователей сразу показываем режим покупателя
        bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Вы перешли в режим покупателя.",
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
        )

# Обработчики для регистрации
start_handler = telebot.TeleBot.message_handler(start_command)
mode_selector_handler = telebot.TeleBot.callback_query_handler(mode_selector)
back_to_start_handler = telebot.TeleBot.callback_query_handler(back_to_start) 