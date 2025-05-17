import json
import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Union, Any

import config
from models import Category, Product, User, Order, CartItem

class Database:
    def __init__(self):
        self._categories = []
        self._products = []
        self._users = {}  # user_id -> User
        self._orders = []
        self._load_data()
    
    def _load_data(self) -> None:
        """Загрузка данных из файлов"""
        self._load_categories()
        self._load_products()
        self._load_users()
        self._load_orders()
    
    def _load_categories(self) -> None:
        if os.path.exists(config.CATEGORIES_FILE):
            try:
                with open(config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._categories = [Category.from_dict(item) for item in data]
            except Exception as e:
                print(f"Ошибка загрузки категорий: {e}")
                self._categories = []
    
    def _load_products(self) -> None:
        if os.path.exists(config.PRODUCTS_FILE):
            try:
                with open(config.PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._products = [Product.from_dict(item) for item in data]
            except Exception as e:
                print(f"Ошибка загрузки товаров: {e}")
                self._products = []
    
    def _load_users(self) -> None:
        if os.path.exists(config.USERS_FILE):
            try:
                with open(config.USERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._users = {int(user_id): User.from_dict(user_data) 
                                 for user_id, user_data in data.items()}
            except Exception as e:
                print(f"Ошибка загрузки пользователей: {e}")
                self._users = {}
    
    def _load_orders(self) -> None:
        if os.path.exists(config.ORDERS_FILE):
            try:
                with open(config.ORDERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._orders = [Order.from_dict(item) for item in data]
            except Exception as e:
                print(f"Ошибка загрузки заказов: {e}")
                self._orders = []
    
    def _save_categories(self) -> None:
        """Сохранение категорий в файл"""
        os.makedirs(os.path.dirname(config.CATEGORIES_FILE), exist_ok=True)
        with open(config.CATEGORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump([category.to_dict() for category in self._categories], f, ensure_ascii=False, indent=2)
    
    def _save_products(self) -> None:
        """Сохранение товаров в файл"""
        os.makedirs(os.path.dirname(config.PRODUCTS_FILE), exist_ok=True)
        with open(config.PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump([product.to_dict() for product in self._products], f, ensure_ascii=False, indent=2)
    
    def _save_users(self) -> None:
        """Сохранение пользователей в файл"""
        os.makedirs(os.path.dirname(config.USERS_FILE), exist_ok=True)
        with open(config.USERS_FILE, 'w', encoding='utf-8') as f:
            data = {str(user_id): user.to_dict() for user_id, user in self._users.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_orders(self) -> None:
        """Сохранение заказов в файл"""
        os.makedirs(os.path.dirname(config.ORDERS_FILE), exist_ok=True)
        with open(config.ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([order.to_dict() for order in self._orders], f, ensure_ascii=False, indent=2)
    
    def save_all(self) -> None:
        """Сохранение всех данных"""
        self._save_categories()
        self._save_products()
        self._save_users()
        self._save_orders()
    
    def backup_data(self) -> str:
        """Создание резервной копии данных"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(config.BACKUP_DIR, timestamp)
        os.makedirs(backup_path, exist_ok=True)
        
        # Сначала сохраняем текущие данные
        self.save_all()
        
        # Копируем файлы в резервную директорию
        for filename in [config.CATEGORIES_FILE, config.PRODUCTS_FILE, 
                         config.USERS_FILE, config.ORDERS_FILE]:
            if os.path.exists(filename):
                shutil.copy2(filename, os.path.join(backup_path, os.path.basename(filename)))
        
        return backup_path
    
    def restore_data(self, backup_path: str) -> bool:
        """Восстановление данных из резервной копии"""
        try:
            for filename in [config.CATEGORIES_FILE, config.PRODUCTS_FILE, 
                             config.USERS_FILE, config.ORDERS_FILE]:
                source = os.path.join(backup_path, os.path.basename(filename))
                if os.path.exists(source):
                    shutil.copy2(source, filename)
            
            # Перезагружаем данные
            self._load_data()
            return True
        except Exception as e:
            print(f"Ошибка восстановления данных: {e}")
            return False
    
    def list_backups(self) -> List[str]:
        """Список всех доступных резервных копий"""
        if not os.path.exists(config.BACKUP_DIR):
            return []
        return sorted(os.listdir(config.BACKUP_DIR))
    
    # Методы для работы с категориями
    def get_categories(self) -> List[Category]:
        return self._categories
    
    def get_category(self, category_id: int) -> Optional[Category]:
        for category in self._categories:
            if category.id == category_id:
                return category
        return None
    
    def add_category(self, name: str) -> Category:
        category_id = 1
        if self._categories:
            category_id = max(category.id for category in self._categories) + 1
        
        category = Category(id=category_id, name=name)
        self._categories.append(category)
        self._save_categories()
        return category
    
    def update_category(self, category_id: int, name: str) -> Optional[Category]:
        category = self.get_category(category_id)
        if category:
            category.name = name
            self._save_categories()
            return category
        return None
    
    def delete_category(self, category_id: int) -> bool:
        for i, category in enumerate(self._categories):
            if category.id == category_id:
                self._categories.pop(i)
                # Удаляем все товары в этой категории
                self._products = [p for p in self._products if p.category_id != category_id]
                self._save_categories()
                self._save_products()
                return True
        return False
    
    # Методы для работы с товарами
    def get_products(self, category_id: Optional[int] = None) -> List[Product]:
        if category_id is not None:
            return [p for p in self._products if p.category_id == category_id]
        return self._products
    
    def get_available_products(self, category_id: Optional[int] = None) -> List[Product]:
        products = self.get_products(category_id)
        return [p for p in products if p.available]
    
    def get_product(self, product_id: int) -> Optional[Product]:
        for product in self._products:
            if product.id == product_id:
                return product
        return None
    
    def add_product(self, name: str, category_id: int, price: float, 
                   unit: str, image_path: Optional[str] = None) -> Optional[Product]:
        if not self.get_category(category_id):
            return None
        
        product_id = 1
        if self._products:
            product_id = max(product.id for product in self._products) + 1
        
        product = Product(
            id=product_id,
            name=name,
            category_id=category_id,
            price=price,
            unit=unit,
            image_path=image_path,
            available=True
        )
        self._products.append(product)
        self._save_products()
        return product
    
    def update_product(self, product_id: int, **kwargs) -> Optional[Product]:
        product = self.get_product(product_id)
        if not product:
            return None
        
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        self._save_products()
        return product
    
    def delete_product(self, product_id: int) -> bool:
        for i, product in enumerate(self._products):
            if product.id == product_id:
                self._products.pop(i)
                self._save_products()
                return True
        return False
    
    def search_products(self, query: str) -> List[Product]:
        query = query.lower()
        return [p for p in self._products if query in p.name.lower() and p.available]
    
    # Методы для работы с пользователями
    def get_user(self, user_id: int) -> User:
        if user_id not in self._users:
            self._users[user_id] = User(id=user_id)
            self._save_users()
        return self._users[user_id]
    
    def update_user(self, user_id: int, **kwargs) -> User:
        user = self.get_user(user_id)
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self._save_users()
        return user
    
    def get_favorite_products(self, user_id: int) -> List[Product]:
        user = self.get_user(user_id)
        return [p for p in self._products if p.id in user.favorites and p.available]
    
    # Методы для работы с заказами
    def create_order(self, user_id: int, phone: str, address: str, delivery_time: Optional[str] = None) -> Optional[Order]:
        user = self.get_user(user_id)
        if not user.cart:
            return None
        
        order_id = 1
        if self._orders:
            order_id = max(order.id for order in self._orders) + 1
        
        # Вычисляем общую сумму заказа
        total = 0.0
        for cart_item in user.cart:
            product = self.get_product(cart_item.product_id)
            if product:
                total += product.price * cart_item.quantity
        
        order = Order(
            id=order_id,
            user_id=user_id,
            items=user.cart.copy(),
            phone=phone,
            address=address,
            delivery_time=delivery_time,
            total=total
        )
        self._orders.append(order)
        
        # Очищаем корзину пользователя
        user.clear_cart()
        
        self._save_orders()
        self._save_users()
        return order
    
    def get_orders(self, user_id: Optional[int] = None) -> List[Order]:
        if user_id is not None:
            return [order for order in self._orders if order.user_id == user_id]
        return self._orders
    
    def get_all_orders(self) -> List[Order]:
        """Получить все заказы"""
        return self._orders
    
    def get_order(self, order_id: int) -> Optional[Order]:
        for order in self._orders:
            if order.id == order_id:
                return order
        return None
    
    def update_order_status(self, order_id: int, status: str) -> Optional[Order]:
        order = self.get_order(order_id)
        if order:
            order.status = status
            self._save_orders()
            return order
        return None
        
    def update_product_availability(self, product_id: int, available: bool) -> Optional[Product]:
        """Обновление статуса доступности товара"""
        return self.update_product(product_id, available=available)

# Создаем глобальный экземпляр базы данных
db = Database() 