from telebot.handler_backends import State, StatesGroup

# Определение состояний для FSM (Finite State Machine)
class BotStates(StatesGroup):
    # Основные состояния
    START = State()
    CUSTOMER_MODE = State()
    ADMIN_MODE = State()
    
    # Состояния для администратора
    CATEGORY_NAME_INPUT = State()
    CATEGORY_EDIT_SELECT = State()
    CATEGORY_EDIT_NAME_INPUT = State()
    CATEGORY_DELETE_SELECT = State()
    
    # Состояния для работы с товарами
    PRODUCT_CATEGORY_SELECT = State()
    PRODUCT_NAME_INPUT = State()
    PRODUCT_PRICE_INPUT = State()
    PRODUCT_UNIT_SELECT = State()
    PRODUCT_IMAGE_INPUT = State()
    PRODUCT_EDIT_SELECT = State()
    PRODUCT_EDIT_MENU = State()
    PRODUCT_EDIT_NAME_INPUT = State()
    PRODUCT_EDIT_PRICE_INPUT = State()
    PRODUCT_EDIT_IMAGE_INPUT = State()
    PRODUCT_DELETE_SELECT = State()
    BACKUP_SELECT = State()
    ANALYTICS_VIEW = State()
    
    # Состояния для покупателя
    CATEGORY_VIEW = State()
    PRODUCT_DETAIL = State()
    FAVORITES_VIEW = State()
    SEARCH_INPUT = State()
    SEARCH_RESULTS = State()
    
    # Состояния для корзины
    CART_VIEW = State()
    CHECKOUT_START = State()
    PHONE_INPUT = State()
    ADDRESS_INPUT = State()
    DELIVERY_TIME_SELECT = State()
    
    # Состояния для работы с заказами
    ORDERS_LIST = State()
    ORDER_DETAIL = State() 