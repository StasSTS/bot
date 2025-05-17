import os
import logging
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

import config
import keyboards
import handlers.start as start
import handlers.admin as admin
import handlers.customer as customer
import handlers.cart as cart
import handlers.orders as orders
from database import db
from states import BotStates

from flask import Flask
from threading import Thread

# Изменяем импорт werkzeug для совместимости
try:
    from werkzeug.utils import url_quote
except ImportError:
    from werkzeug.urls import url_quote

app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Запуск бота"""
    # Проверка наличия токена
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не найден. Создайте файл .env с переменной BOT_TOKEN.")
        return
    
    # Создание директории для изображений товаров
    os.makedirs("data/images", exist_ok=True)
    
    # Инициализация бота с хранилищем состояний
    from telebot.storage import StateMemoryStorage
    state_storage = StateMemoryStorage()
    bot = telebot.TeleBot(config.BOT_TOKEN, state_storage=state_storage)
    
    # Запуск веб-сервера в отдельном потоке для предотвращения засыпания
    Thread(target=run_web_server).start()
    
    # Регистрация обработчиков команд
    
    # Команда /start
    @bot.message_handler(commands=['start'])
    def start_command(message):
        start.start_command(bot, message)
    
    # Функция для проверки прав администратора и перенаправления
    def check_admin_rights(bot: telebot.TeleBot, call: types.CallbackQuery) -> bool:
        """
        Проверяет права администратора у пользователя.
        Если пользователь не админ, перенаправляет его в режим покупателя и возвращает False.
        Если пользователь админ, возвращает True.
        """
        logger = logging.getLogger(__name__)
        
        # Если пользователь не админ, перенаправляем его и возвращаем False
        if call.from_user.id != config.ADMIN_USER_ID:
            logger.warning(f"Попытка неавторизованного доступа к админ-функциям: user_id={call.from_user.id}")
            
            # Перенаправляем пользователя в режим покупателя
            bot.set_state(call.from_user.id, BotStates.CUSTOMER_MODE, call.message.chat.id)
            
            try:
                bot.edit_message_text(
                    "У вас нет прав доступа к режиму администратора. Вы перенаправлены в режим покупателя.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                )
            except ApiTelegramException as e:
                # Если не удалось отредактировать сообщение, отправляем новое
                logger.error(f"Ошибка при редактировании сообщения: {str(e)}")
                try:
                    bot.send_message(
                        chat_id=call.message.chat.id,
                        text="У вас нет прав доступа к режиму администратора. Вы перенаправлены в режим покупателя.",
                        reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                    )
                except Exception as e2:
                    logger.error(f"Критическая ошибка при отправке сообщения: {str(e2)}")
            
            return False
        
        return True

    # Обработчик callback-запросов (нажатия на inline-кнопки)
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        # Получение текущего состояния пользователя
        user_id = call.from_user.id
        current_state = bot.get_state(user_id, call.message.chat.id)
        
        # Обработка общей кнопки "Назад" для всех состояний
        if call.data == "back":
            # Для состояний администратора
            if current_state == BotStates.CATEGORY_NAME_INPUT.name or \
               current_state == BotStates.CATEGORY_EDIT_SELECT.name or \
               current_state == BotStates.CATEGORY_EDIT_NAME_INPUT.name or \
               current_state == BotStates.CATEGORY_DELETE_SELECT.name or \
               current_state == BotStates.ANALYTICS_VIEW.name or \
               current_state == BotStates.BACKUP_SELECT.name:
                # Проверяем права администратора
                if check_admin_rights(bot, call):
                    admin.back_to_admin_main(bot, call)
                return
                
            # Особая обработка для редактирования товаров
            elif current_state == BotStates.PRODUCT_EDIT_NAME_INPUT.name or \
                 current_state == BotStates.PRODUCT_EDIT_PRICE_INPUT.name or \
                 current_state == BotStates.PRODUCT_EDIT_IMAGE_INPUT.name:
                if check_admin_rights(bot, call):
                    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                        product_id = data.get('edit_product_id')
                        if not product_id:
                            product_id = data.get('current_product_id')
                    if product_id:
                        # Возвращаемся в меню редактирования товара
                        admin.edit_product_menu(bot, call)
                    else:
                        # Если ID не найден, возвращаемся в главное меню админа
                        admin.back_to_admin_main(bot, call)
                return
                
            # Обработка для состояния ввода телефона при оформлении заказа
            elif current_state == BotStates.PHONE_INPUT.name:
                # Возвращаемся к экрану оформления заказа
                cart.checkout_start(bot, call)
                return
                
            # Обработка для состояния ввода адреса при оформлении заказа
            elif current_state == BotStates.ADDRESS_INPUT.name:
                # Возвращаемся к экрану ввода телефона
                cart.phone_input_start(bot, call)
                return
        
        # Обработка выбора режима
        if call.data.startswith("mode_"):
            start.mode_selector(bot, call)
        
        # Обработка возврата к начальному экрану
        elif call.data == "back_to_start":
            start.back_to_start(bot, call)
        
        # Обработка просмотра деталей заказа (доступно в любом состоянии)
        elif call.data.startswith("view_order_"):
            orders.view_order_detail(bot, call)
        
        # Обработка режима администратора
        elif current_state == BotStates.ADMIN_MODE.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            # Обработка команд администратора
            if call.data == "admin_add_category":
                admin.add_category_start(bot, call)
            elif call.data == "admin_edit_category":
                admin.edit_category_select(bot, call)
            elif call.data == "admin_delete_category":
                admin.delete_category_select(bot, call)
            elif call.data == "admin_add_product":
                admin.add_product_start(bot, call)
            elif call.data == "admin_edit_product":
                admin.edit_product_select(bot, call)
            elif call.data == "admin_orders":
                orders.view_orders(bot, call)
            elif call.data == "admin_delete_product":
                admin.delete_product_select(bot, call)
            elif call.data == "admin_save_data":
                admin.save_data(bot, call)
            elif call.data == "admin_load_data":
                admin.load_data_list(bot, call)
            elif call.data == "admin_analytics":
                admin.show_analytics(bot, call)
            elif call.data == "back":
                start.back_to_start(bot, call)
        
        # Обработка выбора категории для редактирования
        elif current_state == BotStates.CATEGORY_EDIT_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("edit_category_"):
                admin.edit_category_name_input(bot, call)
        
        # Обработка выбора категории для удаления
        elif current_state == BotStates.CATEGORY_DELETE_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("delete_category_"):
                admin.delete_category_confirm(bot, call)
        
        # Обработка выбора категории при добавлении товара
        elif current_state == BotStates.PRODUCT_CATEGORY_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("product_category_"):
                admin.product_category_selected(bot, call)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
        
        # Обработка выбора единицы измерения товара
        elif current_state == BotStates.PRODUCT_UNIT_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("unit_"):
                admin.product_unit_selected(bot, call)
            elif call.data == "back":
                # Возвращаемся к вводу цены
                with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                    product_name = data.get('product_name', '')
                
                bot.set_state(call.from_user.id, BotStates.PRODUCT_PRICE_INPUT, call.message.chat.id)
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(keyboards.BACK_BUTTON)
                
                bot.edit_message_text(
                    f"Название товара: {product_name}\n"
                    f"Введите цену товара (в рублях, например: 99.90):",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboard
                )
        
        # Обработка загрузки изображения товара
        elif current_state == BotStates.PRODUCT_IMAGE_INPUT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data == "skip_image":
                admin.product_image_skipped(bot, call)
            elif call.data == "back":
                # Возвращаемся к выбору единицы измерения
                with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                    product_name = data.get('product_name', '')
                    product_price = data.get('product_price', 0)
                
                bot.set_state(call.from_user.id, BotStates.PRODUCT_UNIT_SELECT, call.message.chat.id)
                
                bot.edit_message_text(
                    f"Название: {product_name}\n"
                    f"Цена: {utils.format_money(product_price)}\n"
                    f"Выберите единицу измерения:",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    reply_markup=keyboards.get_unit_selection_keyboard()
                )
        
        # Обработка выбора товара для редактирования
        elif current_state == BotStates.PRODUCT_EDIT_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("edit_product_"):
                admin.edit_product_menu(bot, call)
            elif call.data.startswith("edit_category_products_"):
                # Выбор товара из категории для редактирования
                category_id = int(call.data.split("_")[-1])
                admin.show_products_for_edit(bot, call, category_id)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
                
        # Обработка выбора товара для удаления
        elif current_state == BotStates.PRODUCT_DELETE_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("delete_category_products_"):
                # Выбор товара из категории для удаления
                category_id = int(call.data.split("_")[-1])
                admin.show_products_for_delete(bot, call, category_id)
            elif call.data.startswith("delete_product_"):
                # Подтверждение удаления товара
                product_id = int(call.data.split("_")[-1])
                admin.delete_product_confirm(bot, call, product_id)
            elif call.data.startswith("confirm_delete_product_"):
                # Удаление товара после подтверждения
                product_id = int(call.data.split("_")[-1])
                admin.delete_product_execute(bot, call, product_id)
            elif call.data == "cancel_delete_product":
                # Отмена удаления
                admin.back_to_admin_main(bot, call)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
        
        # Обработка меню редактирования товара
        elif current_state == BotStates.PRODUCT_EDIT_MENU.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("edit_product_available_"):
                admin.toggle_product_availability(bot, call)
            elif call.data.startswith("edit_product_name_"):
                admin.edit_product_name_start(bot, call)
            elif call.data.startswith("edit_product_price_"):
                admin.edit_product_price_start(bot, call)
            elif call.data.startswith("edit_product_image_"):
                admin.edit_product_image_start(bot, call)
            elif call.data == "back":
                admin.edit_product_select(bot, call)
        
        # Обработка режима покупателя
        elif current_state == BotStates.CUSTOMER_MODE.name:
            if call.data.startswith("category_"):
                customer.category_selected(bot, call)
            elif call.data == "favorites":
                customer.view_favorites(bot, call)
            elif call.data == "search":
                customer.search_start(bot, call)
            elif call.data == "cart":
                try:
                    logger.info(f"Нажатие на кнопку корзины: user_id={call.from_user.id}")
                    cart.view_cart(bot, call)
                except Exception as e:
                    logger.error(f"Ошибка при загрузке корзины: {str(e)}")
                    try:
                        bot.answer_callback_query(call.id, "Ошибка при загрузке корзины")
                        bot.edit_message_text(
                            "Произошла ошибка при загрузке корзины. Попробуйте позже.",
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            reply_markup=keyboards.get_customer_main_keyboard_with_cart(call.from_user.id)
                        )
                    except Exception as e2:
                        logger.error(f"Ошибка при обработке ошибки корзины: {str(e2)}")
                        try:
                            bot.send_message(
                                call.message.chat.id,
                                "Произошла ошибка. Пожалуйста, отправьте команду /start для перезапуска бота."
                            )
                        except:
                            pass
        
        # Обработка выбора товаров в категории
        elif current_state == BotStates.CATEGORY_VIEW.name:
            if call.data.startswith("product_"):
                customer.product_selected(bot, call)
            elif call.data == "back":
                customer.back_to_customer_main(bot, call)
            elif call.data == "cart":
                try:
                    logger.info(f"Нажатие на кнопку корзины в категории: user_id={call.from_user.id}")
                    cart.view_cart(bot, call)
                except Exception as e:
                    logger.error(f"Ошибка при просмотре корзины из категории: {str(e)}")
                    try:
                        bot.answer_callback_query(call.id, "Ошибка при загрузке корзины")
                        # Возвращаемся к списку категорий
                        customer.back_to_customer_main(bot, call)
                    except:
                        pass
        
        # Обработка просмотра деталей товара
        elif current_state == BotStates.PRODUCT_DETAIL.name:
            if call.data.startswith("add_favorite_"):
                customer.add_to_favorites(bot, call)
            elif call.data.startswith("remove_favorite_"):
                customer.remove_from_favorites(bot, call)
            elif call.data.startswith("add_to_cart_"):
                customer.add_to_cart(bot, call)
            elif call.data.startswith("remove_from_cart_"):
                customer.remove_from_cart(bot, call)
            elif call.data == "back":
                customer.back_to_customer_main(bot, call)
            elif call.data == "cart":
                try:
                    logger.info(f"Нажатие на кнопку корзины в просмотре товара: user_id={call.from_user.id}")
                    cart.view_cart(bot, call)
                except Exception as e:
                    logger.error(f"Ошибка при просмотре корзины из просмотра товара: {str(e)}")
                    try:
                        bot.answer_callback_query(call.id, "Ошибка при загрузке корзины")
                        # Возвращаемся к просмотру товара или в главное меню
                        with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
                            product_id = data.get('current_product_id')
                            if product_id:
                                product = db.get_product(product_id)
                                if product:
                                    customer.product_selected(bot, call)
                                    return
                        customer.back_to_customer_main(bot, call)
                    except:
                        pass
        
        # Обработка избранного
        elif current_state == BotStates.FAVORITES_VIEW.name:
            if call.data.startswith("product_"):
                customer.product_selected(bot, call)
            elif call.data == "back":
                customer.back_to_customer_main(bot, call)
            elif call.data == "cart":
                try:
                    logger.info(f"Нажатие на кнопку корзины в избранном: user_id={call.from_user.id}")
                    cart.view_cart(bot, call)
                except Exception as e:
                    logger.error(f"Ошибка при просмотре корзины из избранного: {str(e)}")
                    try:
                        bot.answer_callback_query(call.id, "Ошибка при загрузке корзины")
                        customer.back_to_customer_main(bot, call)
                    except:
                        pass
        
        # Обработка результатов поиска
        elif current_state == BotStates.SEARCH_RESULTS.name:
            if call.data.startswith("product_"):
                customer.product_selected(bot, call)
            elif call.data == "back":
                customer.back_to_customer_main(bot, call)
            elif call.data == "cart":
                try:
                    logger.info(f"Нажатие на кнопку корзины в результатах поиска: user_id={call.from_user.id}")
                    cart.view_cart(bot, call)
                except Exception as e:
                    logger.error(f"Ошибка при просмотре корзины из результатов поиска: {str(e)}")
                    try:
                        bot.answer_callback_query(call.id, "Ошибка при загрузке корзины")
                        customer.back_to_customer_main(bot, call)
                    except:
                        pass
        
        # Обработка корзины
        elif current_state == BotStates.CART_VIEW.name:
            if call.data == "checkout":
                cart.checkout_start(bot, call)
            elif call.data == "clear_cart":
                cart.clear_cart(bot, call)
            elif call.data == "back":
                customer.back_to_customer_main(bot, call)
        
        # Обработка оформления заказа
        elif current_state == BotStates.CHECKOUT_START.name:
            if call.data == "use_saved_data":
                cart.use_saved_data(bot, call)
            elif call.data == "phone_input":
                cart.phone_input_start(bot, call)
            elif call.data == "back":
                cart.view_cart(bot, call)
        
        # Обработка состояния поиска
        elif current_state == BotStates.SEARCH_INPUT.name:
            if call.data == "back":
                customer.back_to_customer_main(bot, call)
        
        # Обработка выбора времени доставки
        elif current_state == BotStates.DELIVERY_TIME_SELECT.name:
            if call.data.startswith("delivery_time_"):
                cart.delivery_time_selected(bot, call)
            elif call.data == "back":
                # Возвращаемся к предыдущему шагу (оформление заказа)
                cart.checkout_start(bot, call)
                
        # Обработка списка заказов
        elif current_state == BotStates.ORDERS_LIST.name:
            if call.data.startswith("view_order_"):
                orders.view_order_detail(bot, call)
            elif call.data.startswith("filter_orders_"):
                orders.handle_order_filter(bot, call)
            elif call.data.startswith("sort_orders_"):
                orders.handle_order_sort(bot, call)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
                
        # Обработка детальной информации о заказе
        elif current_state == BotStates.ORDER_DETAIL.name:
            if call.data.startswith("complete_order_") or call.data.startswith("reopen_order_"):
                orders.change_order_status(bot, call)
            elif call.data == "back_to_orders":
                orders.back_to_orders(bot, call)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
                
        # Обработка выбора резервной копии
        elif current_state == BotStates.BACKUP_SELECT.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data.startswith("load_backup_"):
                # Загрузка выбранной резервной копии
                backup_name = call.data[len("load_backup_"):]
                admin.load_backup(bot, call, backup_name)
            elif call.data == "back":
                admin.back_to_admin_main(bot, call)
                
        # Обработка состояния аналитики
        elif current_state == BotStates.ANALYTICS_VIEW.name:
            # Проверка прав администратора
            if not check_admin_rights(bot, call):
                return
                
            if call.data == "back":
                admin.back_to_admin_main(bot, call)
        
        # Обработка состояния ввода телефона
        elif current_state == BotStates.PHONE_INPUT.name:
            if call.data.startswith("phone_digit_"):
                # Обработка нажатия на цифру виртуальной клавиатуры
                cart.process_phone_digit(bot, call)
            elif call.data == "phone_delete":
                # Обработка удаления последней цифры
                cart.process_phone_delete(bot, call)
            elif call.data == "phone_submit":
                # Обработка подтверждения ввода
                cart.process_phone_submit(bot, call)
            elif call.data == "back":
                # Возвращаемся к экрану оформления заказа
                cart.checkout_start(bot, call)
    
    # Функция для проверки прав администратора при обработке сообщений
    def check_admin_rights_message(bot: telebot.TeleBot, message: types.Message) -> bool:
        """
        Проверяет права администратора у пользователя при обработке сообщений.
        Если пользователь не админ, перенаправляет его в режим покупателя и возвращает False.
        Если пользователь админ, возвращает True.
        """
        logger = logging.getLogger(__name__)
        
        # Если пользователь не админ, перенаправляем его и возвращаем False
        if message.from_user.id != config.ADMIN_USER_ID:
            logger.warning(f"Попытка неавторизованного доступа к админ-функциям: user_id={message.from_user.id}")
            
            # Перенаправляем пользователя в режим покупателя
            bot.set_state(message.from_user.id, BotStates.CUSTOMER_MODE, message.chat.id)
            
            try:
                bot.send_message(
                    chat_id=message.chat.id,
                    text="У вас нет прав доступа к режиму администратора. Вы перенаправлены в режим покупателя.",
                    reply_markup=keyboards.get_customer_main_keyboard_with_cart(message.from_user.id)
                )
            except Exception as e:
                logger.error(f"Критическая ошибка при отправке сообщения: {str(e)}")
            
            return False
        
        return True

    # Обработчик текстовых сообщений
    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        user_id = message.from_user.id
        current_state = bot.get_state(user_id, message.chat.id)
        
        # Обработка ввода имени категории
        if current_state == BotStates.CATEGORY_NAME_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.add_category_name(bot, message)
        
        # Обработка ввода нового имени категории
        elif current_state == BotStates.CATEGORY_EDIT_NAME_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.edit_category_name_save(bot, message)
        
        # Обработка ввода названия товара
        elif current_state == BotStates.PRODUCT_NAME_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.product_name_input(bot, message)
        
        # Обработка ввода цены товара
        elif current_state == BotStates.PRODUCT_PRICE_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.product_price_input(bot, message)
        
        # Обработка ввода нового названия товара при редактировании
        elif current_state == BotStates.PRODUCT_EDIT_NAME_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.edit_product_name_save(bot, message)
                
        # Обработка ввода новой цены товара при редактировании
        elif current_state == BotStates.PRODUCT_EDIT_PRICE_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.edit_product_price_save(bot, message)
        
        # Обработка ввода поискового запроса
        elif current_state == BotStates.SEARCH_INPUT.name:
            customer.search_process(bot, message)
        
        # Обработка ввода телефона
        elif current_state == BotStates.PHONE_INPUT.name:
            cart.process_phone(bot, message)
        
        # Обработка ввода адреса
        elif current_state == BotStates.ADDRESS_INPUT.name:
            cart.process_address(bot, message)
    
    # Обработчик фото (для добавления и редактирования товаров)
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        user_id = message.from_user.id
        current_state = bot.get_state(user_id, message.chat.id)
        
        # Обработка загрузки изображения товара при создании
        if current_state == BotStates.PRODUCT_IMAGE_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.product_image_uploaded(bot, message)
        # Обработка загрузки изображения товара при редактировании
        elif current_state == BotStates.PRODUCT_EDIT_IMAGE_INPUT.name:
            if check_admin_rights_message(bot, message):
                admin.edit_product_image_upload(bot, message)
        # Здесь будет обработка загрузки фото товаров
        # для других состояний, связанных с редактированием товаров
    
    logger.info("Бот запущен")
    bot.infinity_polling()

if __name__ == "__main__":
    main() 