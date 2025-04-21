from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='customer')  # customer, restaurant, delivery
    is_profile_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Orders for Customers
    customer_orders = db.relationship('Order', foreign_keys='Order.customer_id', backref='customer', lazy='dynamic')
    
    # Relationship for Restaurant
    restaurant_profile = db.relationship('Restaurant', backref='owner', uselist=False)
    
    # Relationship for Delivery Partner
    delivery_orders = db.relationship('Order', foreign_keys='Order.delivery_partner_id', backref='delivery_partner', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cuisine_type = db.Column(db.String(50), nullable=True)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    is_open = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy='dynamic')
    orders = db.relationship('Order', backref='restaurant', lazy='dynamic')
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cuisine_type': self.cuisine_type,
            'address': self.address,
            'phone': self.phone,
            'image_url': self.image_url,
            'rating': self.rating,
            'is_open': self.is_open
        }

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    order_items = db.relationship('OrderItem', backref='menu_item', lazy='dynamic')
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, ready_for_pickup, picking, delivering, completed, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')  # cash, online
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    
    def __repr__(self):
        return f'<Order {self.id}>'
    
    @property
    def customer_name(self):
        return self.customer.username
    
    @property
    def order_items_display(self):
        items_text = [f"{item.quantity}x {item.menu_item.name}" for item in self.items.all()]
        if len(items_text) > 2:
            return f"{', '.join(items_text[:2])} and {len(items_text) - 2} more"
        return ', '.join(items_text)
    
    @property
    def item_count(self):
        """Get total number of items in the order"""
        return sum(item.quantity for item in self.items.all())

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)  # Store price at time of order
    
    def __repr__(self):
        return f'<OrderItem {self.menu_item_id} x{self.quantity}>'
