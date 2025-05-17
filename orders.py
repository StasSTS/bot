import logging
import telebot
from telebot import types
from typing import List, Dict, Any, Optional
from datetime import datetime

import keyboards
import utils
import config
import handlers.admin as admin
from database import db
from states import BotStates

# Состояния для работы с заказами
(
    ORDERS_LIST,
    ORDER_DETAIL
) = range(2)

# Переменные для хранения текущих параметров фильтрации и сортировки
# Значения по умолчанию: фильтр - все заказы, сортировка - по дате (сначала новые)
filter_type = "all"  # "all", "new", "completed"
sort_type = "date"   # "date", "user"
sort_direction = "desc"  # "asc", "desc"

def view_orders(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать список заказов."""
    logger = logging.getLogger(__name__)
    logger.info(f"Просмотр списка заказов администратором: user_id={call.from_user.id}")
    
    try:
        bot.answer_callback_query(call.id)
        
        # Получаем заказы с учетом текущего фильтра и сортировки
        orders = get_filtered_orders(filter_type, sort_type, sort_direction)
        logger.info(f"Получено заказов: {len(orders)} с фильтром={filter_type}, сортировкой={sort_type}, направлением={sort_direction}")
        
        # Устанавливаем состояние ORDERS_LIST
        bot.set_state(call.from_user.id, BotStates.ORDERS_LIST, call.message.chat.id)
        
        # Получаем клавиатуру для списка заказов
        keyboard = keyboards.get_orders_list_keyboard(orders, filter_type)
        if not keyboard:
            logger.error("Ошибка при создании клавиатуры для списка заказов")
            raise ValueError("Ошибка при создании клавиатуры")
        
        try:
            bot.edit_message_text(
                f"Список заказов ({len(orders)}):",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        except telebot.apihelper.ApiTelegramException as e:
            # Перехватываем ошибку "message is not modified"
            if "message is not modified" in str(e):
                logger.info("Сообщение не изменилось, пропускаем обновление")
            else:
                # Если это другая ошибка API, пробрасываем её дальше
                raise
    except Exception as e:
        logger.error(f"Ошибка при просмотре списка заказов: {str(e)}")
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка при загрузке списка заказов")
            admin.back_to_admin_main(bot, call)
        except Exception as e2:
            logger.error(f"Не удалось восстановиться после ошибки просмотра заказов: {str(e2)}")

def get_filtered_orders(filter_type: str, sort_type: str, sort_direction: str) -> List:
    """Получить список заказов с учетом фильтра и сортировки."""
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем все заказы
        all_orders = db.get_orders()
        logger.info(f"Всего получено заказов: {len(all_orders)}")
        
        # Применяем фильтр
        if filter_type == "new":
            filtered_orders = [o for o in all_orders if o.status != "completed"]
        elif filter_type == "completed":
            filtered_orders = [o for o in all_orders if o.status == "completed"]
        else:  # all
            filtered_orders = all_orders
        
        logger.info(f"После фильтрации осталось заказов: {len(filtered_orders)}")
        
        # Проверяем, есть ли заказы после фильтрации
        if not filtered_orders:
            logger.warning(f"Нет заказов, соответствующих фильтру: {filter_type}")
            return []
        
        # Применяем сортировку с проверкой атрибутов
        if sort_type == "date":
            # Проверяем наличие атрибута created_at у всех заказов
            if all(hasattr(o, "created_at") and o.created_at for o in filtered_orders):
                # Сортировка по дате создания
                if sort_direction == "asc":
                    # По возрастанию (сначала старые)
                    sorted_orders = sorted(filtered_orders, key=lambda o: o.created_at)
                else:
                    # По убыванию (сначала новые)
                    sorted_orders = sorted(filtered_orders, key=lambda o: o.created_at, reverse=True)
            else:
                logger.error("Некоторые заказы не имеют атрибута created_at, сортировка невозможна")
                sorted_orders = filtered_orders
                
        elif sort_type == "user":
            # Проверяем наличие атрибута user_id у всех заказов
            if all(hasattr(o, "user_id") for o in filtered_orders):
                # Сортировка по ID пользователя
                if sort_direction == "asc":
                    sorted_orders = sorted(filtered_orders, key=lambda o: o.user_id)
                else:
                    sorted_orders = sorted(filtered_orders, key=lambda o: o.user_id, reverse=True)
            else:
                logger.error("Некоторые заказы не имеют атрибута user_id, сортировка невозможна")
                sorted_orders = filtered_orders
        else:
            # Без сортировки
            sorted_orders = filtered_orders
        
        logger.info(f"Возвращаем отсортированных заказов: {len(sorted_orders)}")
        return sorted_orders
    except Exception as e:
        logger.error(f"Ошибка при фильтрации и сортировке заказов: {str(e)}")
        return []

def view_order_detail(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Показать детальную информацию о заказе."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID заказа из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    order_id = int(data_parts[2])
    
    # Получаем информацию о заказе
    order = db.get_order(order_id)
    
    if not order:
        bot.edit_message_text(
            "Заказ не найден.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.BACK_BUTTON
        )
        return
    
    # Проверяем, является ли пользователь администратором
    is_admin = call.from_user.id == config.ADMIN_USER_ID
    
    # Если пользователь не администратор, проверяем, что это его заказ
    if not is_admin and order.user_id != call.from_user.id:
        bot.edit_message_text(
            "У вас нет доступа к этому заказу.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
        )
        return
    
    # Сохраняем ID заказа в данных состояния
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['current_order_id'] = order_id
    
    # Устанавливаем состояние ORDER_DETAIL только для администратора
    if is_admin:
        bot.set_state(call.from_user.id, BotStates.ORDER_DETAIL, call.message.chat.id)
    
    # Формируем текст с информацией о заказе
    order_text = format_order_details(order)
    
    # Выбираем подходящую клавиатуру в зависимости от того, кто смотрит заказ
    if is_admin:
        # Для администратора - клавиатура с возможностью управления статусом
        keyboard = keyboards.get_order_detail_keyboard(order_id)
    else:
        # Для обычного пользователя - просто кнопка "Назад"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(keyboards.BACK_BUTTON)
    
    bot.edit_message_text(
        order_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboard
    )

def format_order_details(order) -> str:
    """Форматирует детальную информацию о заказе."""
    # Информация о заказе
    date_str = datetime.fromisoformat(order.created_at).strftime("%d.%m.%Y %H:%M")
    status_str = "Выполнен" if order.status == "completed" else "В работе"
    
    # Информация о пользователе
    user = db.get_user(order.user_id)
    user_info = f"👤 {user.username or 'Пользователь'} (ID: {user.id})"
    
    # Детали доставки
    delivery_info = (
        f"📱 Телефон: {order.phone or 'Не указан'}\n"
        f"📍 Адрес: {order.address or 'Не указан'}\n"
        f"🕒 Время доставки: {order.delivery_time or 'Не указано'}"
    )
    
    # Состав заказа
    order_items = []
    total = 0.0
    
    for item in order.items:
        product = db.get_product(item.product_id)
        if not product:
            order_items.append(f"Товар ID:{item.product_id} (не найден) - {item.quantity}")
            continue
            
        price = product.price * item.quantity
        unit_text = "шт" if product.unit == "шт" else "кг"
        order_items.append(f"{product.name} x {item.quantity} {unit_text} = {utils.format_money(price)}")
        total += price
    
    items_text = "\n".join(order_items)
    
    # Собираем весь текст
    return (
        f"📦 Заказ #{order.id}\n"
        f"📅 Дата: {date_str}\n"
        f"🚦 Статус: {status_str}\n\n"
        f"{user_info}\n\n"
        f"{delivery_info}\n\n"
        f"📋 Состав заказа:\n{items_text}\n\n"
        f"💰 Итого: {utils.format_money(total)}"
    )

def handle_order_filter(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка фильтрации заказов."""
    global filter_type
    
    bot.answer_callback_query(call.id)
    
    # Получаем тип фильтра из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        return
    
    # Получаем новый фильтр
    new_filter_type = data_parts[2]  # "all", "new", "completed"
    
    # Если выбран тот же фильтр, что уже применён, не делаем ничего
    if new_filter_type == filter_type:
        return
        
    # Обновляем текущий фильтр
    filter_type = new_filter_type
    
    # Показываем список заказов с новым фильтром
    view_orders(bot, call)

def handle_order_sort(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Обработка сортировки заказов."""
    global sort_type, sort_direction
    
    logger = logging.getLogger(__name__)
    logger.info(f"Обработка сортировки заказов: {call.data}, user_id={call.from_user.id}")
    
    bot.answer_callback_query(call.id)
    
    try:
        # Получаем тип сортировки из callback_data
        data_parts = call.data.split("_")
        if len(data_parts) < 3:
            logger.error(f"Неверный формат callback_data для сортировки: {call.data}")
            return
        
        new_sort_type = data_parts[2]  # "date", "user"
        logger.info(f"Тип сортировки: {new_sort_type}, текущий тип: {sort_type}, направление: {sort_direction}")
        
        # Если нажали на ту же сортировку, меняем направление
        if new_sort_type == sort_type:
            new_sort_direction = "asc" if sort_direction == "desc" else "desc"
            
            # Если направление то же самое (что невозможно в этом коде, но для защиты), не делаем ничего
            if new_sort_direction == sort_direction:
                return
                
            sort_direction = new_sort_direction
        else:
            # Иначе меняем тип сортировки и сбрасываем направление на "desc"
            sort_type = new_sort_type
            sort_direction = "desc"
        
        logger.info(f"Новый тип сортировки: {sort_type}, новое направление: {sort_direction}")
        
        # Получаем отсортированные заказы
        orders = get_filtered_orders(filter_type, sort_type, sort_direction)
        logger.info(f"Получено заказов: {len(orders)}")
        
        # Отображаем заказы с новой сортировкой
        bot.edit_message_text(
            f"Список заказов ({len(orders)}):",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_orders_list_keyboard(orders, filter_type)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сортировке заказов: {str(e)}")
        # Отправляем уведомление о проблеме
        try:
            bot.answer_callback_query(call.id, "Произошла ошибка при сортировке заказов")
            admin.back_to_admin_main(bot, call)
        except Exception as e2:
            logger.error(f"Не удалось восстановиться после ошибки сортировки: {str(e2)}")

def back_to_orders(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Вернуться к списку заказов."""
    bot.answer_callback_query(call.id)
    
    # Устанавливаем состояние ORDERS_LIST
    bot.set_state(call.from_user.id, BotStates.ORDERS_LIST, call.message.chat.id)
    
    # Показываем список заказов
    view_orders(bot, call)

def change_order_status(bot: telebot.TeleBot, call: types.CallbackQuery) -> None:
    """Изменить статус заказа."""
    logger = logging.getLogger(__name__)
    
    bot.answer_callback_query(call.id)
    
    # Получаем ID заказа и действие из callback_data
    data_parts = call.data.split("_")
    if len(data_parts) < 3:
        logger.error(f"Неверный формат callback_data: {call.data}")
        return
    
    action = data_parts[0]  # complete или reopen
    order_id = int(data_parts[2])
    
    # Получаем информацию о заказе
    order = db.get_order(order_id)
    
    if not order:
        bot.edit_message_text(
            "Заказ не найден.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboards.get_orders_list_keyboard(get_filtered_orders(filter_type, sort_type, sort_direction), filter_type)
        )
        return
    
    # Обновляем статус заказа
    new_status = "completed" if action == "complete" else "new"
    db.update_order_status(order_id, new_status)
    
    # Получаем обновленный заказ
    updated_order = db.get_order(order_id)
    
    # Формируем текст с информацией о заказе
    order_text = format_order_details(updated_order)
    
    bot.edit_message_text(
        order_text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=keyboards.get_order_detail_keyboard(order_id)
    )

# Функция для отправки уведомления администратору о новом заказе
def notify_admin_about_new_order(bot: telebot.TeleBot, order_id: int) -> None:
    """Отправляет уведомление администратору о новом заказе."""
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем заказ
        order = db.get_order(order_id)
        if not order:
            logger.error(f"Заказ не найден при отправке уведомления: order_id={order_id}")
            return
        
        # Получаем информацию о пользователе
        user = db.get_user(order.user_id)
        username = user.username or f"Пользователь ID:{user.id}"
        
        # Формируем сообщение
        message = (
            f"🔔 Новый заказ #{order.id}\n"
            f"👤 От: {username}\n"
            f"📱 Телефон: {order.phone or 'Не указан'}\n"
            f"📍 Адрес: {order.address or 'Не указан'}\n"
            f"🕒 Время доставки: {order.delivery_time or 'Не указано'}"
        )
        
        # Создаем клавиатуру с кнопкой просмотра заказа
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("📋 Посмотреть заказ", callback_data=f"view_order_{order.id}"))
        
        # Отправляем уведомление администратору
        bot.send_message(
            chat_id=config.ADMIN_USER_ID,
            text=message,
            reply_markup=keyboard
        )
        
        logger.info(f"Уведомление о новом заказе отправлено администратору: order_id={order_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о заказе администратору: {str(e)}") 