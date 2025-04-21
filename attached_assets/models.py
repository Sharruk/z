from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for customers, restaurant owners, and delivery partners"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)  # Nullable for OAuth users
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(20), default='customer')  # customer, restaurant, delivery
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True, 
                           foreign_keys='Order.customer_id')
    restaurant = db.relationship('Restaurant', backref='owner', lazy=True,
                                uselist=False)
    deliveries = db.relationship('Order', backref='delivery_partner', lazy=True,
                                foreign_keys='Order.delivery_partner_id')
    
    def set_password(self, password):
        """Set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

    def is_profile_complete(self):
        """Check if user profile is complete with required fields"""
        return self.phone is not None and self.address is not None
    
    def __repr__(self):
        return f'<User {self.username}>'


class Restaurant(db.Model):
    """Restaurant model"""
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    cuisine_type = db.Column(db.String(50), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_open = db.Column(db.Boolean, default=True)  # New field for open/closed status
    
    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True,
                                cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='restaurant', lazy=True)
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'


class MenuItem(db.Model):
    """Menu item model for restaurant dishes"""
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    is_vegetarian = db.Column(db.Boolean, default=False)
    is_available = db.Column(db.Boolean, default=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'


class Order(db.Model):
    """Order model for customer orders"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, ready, picking, delivering, completed, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')  # cash, online
    payment_status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True,
                          cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    """Order item model for individual items in an order"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at the time of order
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'