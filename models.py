import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
import config

class Category:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Category':
        return cls(id=data["id"], name=data["name"])

class Product:
    def __init__(self, id: int, name: str, category_id: int, price: float, 
                 unit: str, image_path: Optional[str] = None, available: bool = True):
        self.id = id
        self.name = name
        self.category_id = category_id
        self.price = price
        self.unit = unit  # "кг" или "шт"
        self.image_path = image_path
        self.available = available
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "price": self.price,
            "unit": self.unit,
            "image_path": self.image_path,
            "available": self.available
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        return cls(
            id=data["id"],
            name=data["name"],
            category_id=data["category_id"],
            price=data["price"],
            unit=data["unit"],
            image_path=data.get("image_path"),
            available=data.get("available", True)
        )

class CartItem:
    def __init__(self, product_id: int, quantity: float):
        self.product_id = product_id
        self.quantity = quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "quantity": self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CartItem':
        return cls(product_id=data["product_id"], quantity=data["quantity"])

class User:
    def __init__(self, id: int, username: Optional[str] = None, 
                 phone: Optional[str] = None, address: Optional[str] = None,
                 favorites: Optional[List[int]] = None, is_admin: bool = False):
        self.id = id
        self.username = username
        self.phone = phone
        self.address = address
        self.favorites = favorites or []
        self.cart = []  # Список CartItem
        self.is_admin = is_admin
    
    def add_to_cart(self, product_id: int, quantity: float) -> None:
        for item in self.cart:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        self.cart.append(CartItem(product_id, quantity))
    
    def remove_from_cart(self, product_id: int, quantity: float) -> bool:
        for i, item in enumerate(self.cart):
            if item.product_id == product_id:
                if item.quantity <= quantity:
                    self.cart.pop(i)
                else:
                    item.quantity -= quantity
                return True
        return False
    
    def remove_cart_item(self, product_id: int) -> bool:
        """Полностью удаляет товар из корзины вне зависимости от количества."""
        for i, item in enumerate(self.cart):
            if item.product_id == product_id:
                self.cart.pop(i)
                return True
        return False
    
    def clear_cart(self) -> None:
        self.cart = []
    
    def add_to_favorites(self, product_id: int) -> None:
        if product_id not in self.favorites:
            self.favorites.append(product_id)
    
    def remove_from_favorites(self, product_id: int) -> None:
        if product_id in self.favorites:
            self.favorites.remove(product_id)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "address": self.address,
            "favorites": self.favorites,
            "cart": [item.to_dict() for item in self.cart],
            "is_admin": self.is_admin
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            id=data["id"],
            username=data.get("username"),
            phone=data.get("phone"),
            address=data.get("address"),
            favorites=data.get("favorites", []),
            is_admin=data.get("is_admin", False)
        )
        if "cart" in data:
            user.cart = [CartItem.from_dict(item) for item in data["cart"]]
        return user

class Order:
    def __init__(self, id: int, user_id: int, items: List[CartItem], 
                 status: str = "new", created_at: Optional[str] = None,
                 phone: Optional[str] = None, address: Optional[str] = None,
                 delivery_time: Optional[str] = None, total: float = 0.0):
        self.id = id
        self.user_id = user_id
        self.items = items
        self.status = status  # "new", "processing", "delivered", "cancelled"
        self.created_at = created_at or datetime.now().isoformat()
        self.phone = phone
        self.address = address
        self.delivery_time = delivery_time  # Время доставки (например, "14:00-16:00")
        self.total = total  # Общая сумма заказа
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "created_at": self.created_at,
            "phone": self.phone,
            "address": self.address,
            "delivery_time": self.delivery_time,
            "total": self.total
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            items=[CartItem.from_dict(item) for item in data["items"]],
            status=data.get("status", "new"),
            created_at=data.get("created_at"),
            phone=data.get("phone"),
            address=data.get("address"),
            delivery_time=data.get("delivery_time"),
            total=data.get("total", 0.0)
        ) 