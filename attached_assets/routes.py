from flask import render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from main import app
from models import db, User, Restaurant, MenuItem, Order, OrderItem
from utils import role_required
import json

# Home page 
@app.route('/')
def home():
    """Home page with restaurant listings"""
    restaurants = Restaurant.query.all()
    return render_template('home.html', restaurants=restaurants)

# Search restaurants API
@app.route('/api/search_restaurants', methods=['GET'])
def search_restaurants():
    """API endpoint to search for restaurants"""
    query = request.args.get('query', '')
    
    if not query:
        # Return all restaurants if no query is provided
        restaurants = Restaurant.query.all()
    else:
        # Search for restaurants with names containing the query
        restaurants = Restaurant.query.filter(Restaurant.name.ilike(f'%{query}%')).all()
    
    # Convert restaurant objects to dictionaries
    restaurant_list = []
    for restaurant in restaurants:
        restaurant_list.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'description': restaurant.description,
            'cuisine_type': restaurant.cuisine_type,
            'rating': restaurant.rating,
            'is_open': restaurant.is_open,
            'image_url': restaurant.image_url or '/static/img/default-restaurant.jpg'
        })
    
    return jsonify({'restaurants': restaurant_list})

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password', 'danger')
            return render_template('login.html', error='Invalid email or password')
        
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')
        
        # Redirect based on user role
        if user.role == 'restaurant':
            return redirect(url_for('restaurant_dashboard'))
        elif user.role == 'delivery':
            return redirect(url_for('delivery_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    
    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        # Validate input
        if not name or not email or not password or not confirm_password:
            flash('All fields are required', 'danger')
            return render_template('register.html', error='All fields are required')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html', error='Passwords do not match')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered', 'danger')
            return render_template('register.html', error='Email is already registered')
        
        # Create new user
        new_user = User(
            username=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            phone=phone if phone else None,
            address=address if address else None
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Log in the user
            login_user(new_user)
            
            # If profile is not complete, redirect to complete profile
            if not new_user.is_profile_complete():
                return redirect(url_for('complete_profile'))
                
            # Redirect based on user role
            if new_user.role == 'restaurant':
                # Create a restaurant entry for the restaurant owner
                new_restaurant = Restaurant(
                    name=f"{name}'s Restaurant",  # Default name
                    description="No description available.",
                    address=address if address else "No address provided.",
                    phone=phone if phone else "No phone provided.",
                    cuisine_type="Various",
                    owner_id=new_user.id
                )
                db.session.add(new_restaurant)
                db.session.commit()
                
                flash('Restaurant account created successfully!', 'success')
                return redirect(url_for('restaurant_dashboard'))
            elif new_user.role == 'delivery':
                flash('Delivery partner account created successfully!', 'success')
                return redirect(url_for('delivery_dashboard'))
            else:
                flash('Account created successfully!', 'success')
                return redirect(url_for('user_dashboard'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('register.html', error=f'An error occurred: {str(e)}')
    
    return render_template('register.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

# Complete profile route
@app.route('/complete_profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    """Complete user profile after registration"""
    if current_user.is_profile_complete():
        flash('Your profile is already complete!', 'info')
        
        # Redirect based on user role
        if current_user.role == 'restaurant':
            return redirect(url_for('restaurant_dashboard'))
        elif current_user.role == 'delivery':
            return redirect(url_for('delivery_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not phone or not address:
            flash('Both phone number and address are required.', 'danger')
            return render_template('complete_profile.html')
        
        try:
            current_user.phone = phone
            current_user.address = address
            db.session.commit()
            
            flash('Profile completed successfully!', 'success')
            
            # If this is a restaurant owner and they don't have a restaurant yet, create one
            if current_user.role == 'restaurant' and not current_user.restaurant:
                new_restaurant = Restaurant(
                    name=f"{current_user.username}'s Restaurant",
                    description="No description available.",
                    address=address,
                    phone=phone,
                    cuisine_type="Various",
                    owner_id=current_user.id
                )
                db.session.add(new_restaurant)
                db.session.commit()
            
            # Redirect based on user role
            if current_user.role == 'restaurant':
                return redirect(url_for('restaurant_dashboard'))
            elif current_user.role == 'delivery':
                return redirect(url_for('delivery_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
                
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('complete_profile.html')

# Restaurant details route
@app.route('/restaurant/<int:restaurant_id>')
def restaurant_details(restaurant_id):
    """Show restaurant details and menu items"""
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Only show available menu items if the restaurant is open
    if restaurant.is_open:
        menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    else:
        menu_items = []
    
    return render_template(
        'restaurant_details.html',
        restaurant=restaurant,
        menu_items=menu_items
    )

# User dashboard route
@app.route('/user_dashboard')
@login_required
@role_required('customer')
def user_dashboard():
    """Customer dashboard with orders and favorites"""
    # Get active orders
    active_orders = Order.query.filter_by(
        customer_id=current_user.id
    ).filter(
        Order.status.notin_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).all()
    
    # Get order history
    order_history = Order.query.filter_by(
        customer_id=current_user.id
    ).filter(
        Order.status.in_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template(
        'user_dashboard.html',
        active_orders=active_orders,
        order_history=order_history
    )

# Restaurant dashboard route
@app.route('/restaurant_dashboard')
@login_required
@role_required('restaurant')
def restaurant_dashboard():
    """Restaurant owner dashboard"""
    # Get restaurant owned by current user
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        flash('Restaurant not found. Please contact support.', 'danger')
        return redirect(url_for('home'))
    
    # Get current orders for this restaurant
    current_orders = Order.query.filter_by(
        restaurant_id=restaurant.id
    ).filter(
        Order.status.notin_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).all()
    
    # Get completed orders for this restaurant
    completed_orders = Order.query.filter_by(
        restaurant_id=restaurant.id
    ).filter(
        Order.status.in_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # Get menu items
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant.id).all()
    
    return render_template(
        'restaurant_dashboard.html',
        restaurant=restaurant,
        current_orders=current_orders,
        completed_orders=completed_orders,
        menu_items=menu_items
    )

# Delivery dashboard route
@app.route('/delivery_dashboard')
@login_required
@role_required('delivery')
def delivery_dashboard():
    """Delivery partner dashboard"""
    # Get active deliveries
    active_deliveries = Order.query.filter_by(
        delivery_partner_id=current_user.id
    ).filter(
        Order.status.in_(['picking', 'delivering'])
    ).order_by(Order.created_at.desc()).all()
    
    # Get completed deliveries (history)
    delivery_history = Order.query.filter_by(
        delivery_partner_id=current_user.id, 
        status='completed'
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template(
        'delivery_dashboard.html',
        active_deliveries=active_deliveries,
        delivery_history=delivery_history
    )

# Order details route
@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    """Order details page"""
    # Query the order based on user role
    if current_user.role == 'customer':
        order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first_or_404()
    elif current_user.role == 'restaurant':
        restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
        order = Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first_or_404()
    elif current_user.role == 'delivery':
        order = Order.query.filter_by(id=order_id, delivery_partner_id=current_user.id).first_or_404()
    else:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    return render_template('order_details.html', order=order)

# API Routes

# Toggle restaurant open/closed status
@app.route('/api/restaurant/toggle_status', methods=['POST'])
@login_required
@role_required('restaurant')
def toggle_restaurant_status():
    """Toggle the restaurant's open/closed status"""
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        return jsonify({'success': False, 'error': 'Restaurant not found'})
    
    try:
        # Toggle the status
        restaurant.is_open = not restaurant.is_open
        db.session.commit()
        
        status = 'open' if restaurant.is_open else 'closed'
        return jsonify({
            'success': True, 
            'is_open': restaurant.is_open,
            'message': f'Restaurant is now {status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Toggle menu item availability
@app.route('/api/menu_item/toggle_availability', methods=['POST'])
@login_required
@role_required('restaurant')
def toggle_menu_item_availability():
    """Toggle a menu item's availability"""
    data = request.json
    if not data or 'menu_item_id' not in data:
        return jsonify({'success': False, 'error': 'Menu item ID required'})
    
    menu_item_id = data.get('menu_item_id')
    
    # Get the restaurant first
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant:
        return jsonify({'success': False, 'error': 'Restaurant not found'})
    
    # Now get the menu item and verify it belongs to this restaurant
    menu_item = MenuItem.query.filter_by(id=menu_item_id, restaurant_id=restaurant.id).first()
    if not menu_item:
        return jsonify({'success': False, 'error': 'Menu item not found or does not belong to your restaurant'})
    
    try:
        # Toggle the availability
        menu_item.is_available = not menu_item.is_available
        db.session.commit()
        
        status = 'available' if menu_item.is_available else 'unavailable'
        return jsonify({
            'success': True, 
            'is_available': menu_item.is_available,
            'message': f'"{menu_item.name}" is now {status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Update order status
@app.route('/api/order/update_status', methods=['POST'])
@login_required
def update_order_status():
    """Update the status of an order"""
    data = request.json
    if not data or 'order_id' not in data or 'status' not in data:
        return jsonify({'success': False, 'error': 'Order ID and status required'})
    
    order_id = data.get('order_id')
    new_status = data.get('status')
    
    # Check if the status is valid
    valid_statuses = ['pending', 'preparing', 'ready', 'picking', 'delivering', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'error': 'Invalid status'})
    
    # Query the order based on user role
    if current_user.role == 'restaurant':
        restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
        if not restaurant:
            return jsonify({'success': False, 'error': 'Restaurant not found'})
        
        order = Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first()
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'})
        
        # Restaurant can only update to certain statuses
        allowed_statuses = ['preparing', 'ready', 'cancelled']
        if new_status not in allowed_statuses:
            return jsonify({'success': False, 'error': f'Restaurant cannot set order to {new_status}'})
    
    elif current_user.role == 'delivery':
        order = Order.query.filter_by(id=order_id, delivery_partner_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'})
        
        # Delivery partner can only update to certain statuses
        allowed_statuses = ['picking', 'delivering', 'completed']
        if new_status not in allowed_statuses:
            return jsonify({'success': False, 'error': f'Delivery partner cannot set order to {new_status}'})
    
    elif current_user.role == 'customer':
        order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'})
        
        # Customer can only cancel orders
        if new_status != 'cancelled':
            return jsonify({'success': False, 'error': 'Customers can only cancel orders'})
    
    else:
        return jsonify({'success': False, 'error': 'Invalid user role'})
    
    try:
        # Update the order status
        order.status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Order status updated to {new_status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# Add to cart route
@app.route('/add_to_cart', methods=['POST'])
@login_required
@role_required('customer')
def add_to_cart():
    """Add an item to the cart"""
    menu_item_id = request.form.get('menu_item_id')
    quantity = int(request.form.get('quantity', 1))
    
    # Validate input
    if not menu_item_id or quantity < 0:  # Allow starting with quantity 0
        flash('Invalid request', 'danger')
        return redirect(url_for('home'))
    
    # Get the menu item
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    # Check if the restaurant is open
    restaurant = Restaurant.query.get(menu_item.restaurant_id)
    if not restaurant.is_open:
        flash('This restaurant is currently closed.', 'warning')
        return redirect(url_for('restaurant_details', restaurant_id=restaurant.id))
    
    # Check if the item is available
    if not menu_item.is_available:
        flash('This item is currently unavailable.', 'warning')
        return redirect(url_for('restaurant_details', restaurant_id=menu_item.restaurant_id))
    
    # Initialize cart if it doesn't exist
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if the item is already in the cart
    cart_item_exists = False
    for item in session['cart']:
        if item['menu_item_id'] == int(menu_item_id):
            item['quantity'] += quantity
            cart_item_exists = True
            break
    
    # If not in the cart, add it
    if not cart_item_exists:
        session['cart'].append({
            'menu_item_id': int(menu_item_id),
            'quantity': quantity,
            'price': menu_item.price,
            'restaurant_id': menu_item.restaurant_id
        })
    
    # Update the session
    session.modified = True
    
    flash(f'Added {menu_item.name} to cart', 'success')
    return redirect(url_for('restaurant_details', restaurant_id=menu_item.restaurant_id))

# Cart route
@app.route('/cart')
@login_required
@role_required('customer')
def cart():
    """View the cart"""
    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart_items=[], menu_items=[], total=0)
    
    # Get all menu items in the cart
    menu_item_ids = [item['menu_item_id'] for item in session['cart']]
    menu_items = MenuItem.query.filter(MenuItem.id.in_(menu_item_ids)).all()
    
    # Calculate total
    total = 0
    for item in session['cart']:
        total += item['price'] * item['quantity']
    
    return render_template('cart.html', cart_items=session['cart'], menu_items=menu_items, total=total)

# Update cart route
@app.route('/update_cart', methods=['POST'])
@login_required
@role_required('customer')
def update_cart():
    """Update the cart (change quantity or remove item)"""
    menu_item_id = int(request.form.get('menu_item_id'))
    quantity = int(request.form.get('quantity', 0))
    
    if 'cart' not in session:
        return redirect(url_for('cart'))
    
    # If quantity is 0, remove the item
    if quantity <= 0:
        session['cart'] = [item for item in session['cart'] if item['menu_item_id'] != menu_item_id]
    else:
        # Update the quantity
        for item in session['cart']:
            if item['menu_item_id'] == menu_item_id:
                item['quantity'] = quantity
                break
    
    # Update the session
    session.modified = True
    
    return redirect(url_for('cart'))

# Checkout route
@app.route('/checkout', methods=['POST'])
@login_required
@role_required('customer')
def checkout():
    """Create an order from the cart"""
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    # Check if all items are from the same restaurant
    restaurant_ids = set(item['restaurant_id'] for item in session['cart'])
    if len(restaurant_ids) > 1:
        flash('Items in your cart are from different restaurants', 'danger')
        return redirect(url_for('cart'))
    
    restaurant_id = list(restaurant_ids)[0]
    
    # Check if the restaurant is open
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant.is_open:
        flash('This restaurant is currently closed.', 'warning')
        return redirect(url_for('cart'))
    
    # Calculate total
    total = 0
    for item in session['cart']:
        total += item['price'] * item['quantity']
    
    # Get payment method from form
    payment_method = request.form.get('payment_method', 'cash')
    if payment_method not in ['cash', 'gpay']:
        payment_method = 'cash'  # Default to cash if invalid
    
    # Create the order
    order = Order(
        customer_id=current_user.id,
        restaurant_id=restaurant_id,
        total_amount=total,
        delivery_address=current_user.address,
        status='pending',
        payment_method=payment_method,
        payment_status='pending'
    )
    
    db.session.add(order)
    db.session.flush()  # Get the order ID without committing
    
    # Add order items
    for item in session['cart']:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item['menu_item_id'],
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
    
    try:
        db.session.commit()
        
        # Clear the cart
        session.pop('cart', None)
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_details', order_id=order.id))
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('cart'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500

# Initialize test data
@app.route('/init_db')
def init_db():
    """Initialize test data for development"""
    try:
        # Create test users if they don't exist
        customer = User.query.filter_by(email='customer@example.com').first()
        if not customer:
            customer = User(
                username='Test Customer',
                email='customer@example.com',
                password_hash=generate_password_hash('password'),
                role='customer',
                phone='1234567890',
                address='123 Test St, Test City'
            )
            db.session.add(customer)
        
        restaurant_owner = User.query.filter_by(email='restaurant@example.com').first()
        if not restaurant_owner:
            restaurant_owner = User(
                username='Test Restaurant Owner',
                email='restaurant@example.com',
                password_hash=generate_password_hash('password'),
                role='restaurant',
                phone='0987654321',
                address='456 Restaurant St, Food City'
            )
            db.session.add(restaurant_owner)
        
        delivery_partner = User.query.filter_by(email='delivery@example.com').first()
        if not delivery_partner:
            delivery_partner = User(
                username='Test Delivery Partner',
                email='delivery@example.com',
                password_hash=generate_password_hash('password'),
                role='delivery',
                phone='5555555555',
                address='789 Delivery St, Fast City'
            )
            db.session.add(delivery_partner)
        
        db.session.commit()
        
        # Create test restaurant if it doesn't exist
        test_restaurant = Restaurant.query.filter_by(owner_id=restaurant_owner.id).first()
        if not test_restaurant:
            test_restaurant = Restaurant(
                name='TestBurger Palace',
                description='A delicious test burger joint with amazing food!',
                address='456 Restaurant St, Food City',
                phone='0987654321',
                image_url='https://via.placeholder.com/400x300?text=TestBurger+Palace',
                cuisine_type='American, Burgers, Fast Food',
                rating=4.5,
                is_open=True,
                owner_id=restaurant_owner.id
            )
            db.session.add(test_restaurant)
            db.session.commit()
        
        # Create test menu items if they don't exist
        menu_items_exist = MenuItem.query.filter_by(restaurant_id=test_restaurant.id).first()
        if not menu_items_exist:
            menu_items = [
                MenuItem(
                    name='Classic Burger',
                    description='Juicy beef patty with cheese, lettuce, tomato, and special sauce',
                    price=9.99,
                    image_url='https://via.placeholder.com/300x200?text=Classic+Burger',
                    category='Burgers',
                    is_vegetarian=False,
                    is_available=True,
                    restaurant_id=test_restaurant.id
                ),
                MenuItem(
                    name='Veggie Burger',
                    description='Plant-based patty with cheese, lettuce, tomato, and special sauce',
                    price=8.99,
                    image_url='https://via.placeholder.com/300x200?text=Veggie+Burger',
                    category='Burgers',
                    is_vegetarian=True,
                    is_available=True,
                    restaurant_id=test_restaurant.id
                ),
                MenuItem(
                    name='French Fries',
                    description='Crispy golden fries with your choice of seasoning',
                    price=3.99,
                    image_url='https://via.placeholder.com/300x200?text=French+Fries',
                    category='Sides',
                    is_vegetarian=True,
                    is_available=True,
                    restaurant_id=test_restaurant.id
                ),
                MenuItem(
                    name='Chocolate Milkshake',
                    description='Rich and creamy chocolate milkshake with whipped cream',
                    price=4.99,
                    image_url='https://via.placeholder.com/300x200?text=Chocolate+Milkshake',
                    category='Drinks',
                    is_vegetarian=True,
                    is_available=True,
                    restaurant_id=test_restaurant.id
                ),
            ]
            
            for item in menu_items:
                db.session.add(item)
        
        db.session.commit()
        
        # Create a test order if none exists
        order_exists = Order.query.filter_by(customer_id=customer.id, restaurant_id=test_restaurant.id).first()
        if not order_exists:
            order = Order(
                customer_id=customer.id,
                restaurant_id=test_restaurant.id,
                status='pending',
                total_amount=18.97,
                delivery_address=customer.address,
                payment_method='cash',
                payment_status='pending'
            )
            db.session.add(order)
            db.session.flush()
            
            # Add order items
            burger = MenuItem.query.filter_by(name='Classic Burger', restaurant_id=test_restaurant.id).first()
            fries = MenuItem.query.filter_by(name='French Fries', restaurant_id=test_restaurant.id).first()
            
            if burger and fries:
                order_items = [
                    OrderItem(
                        order_id=order.id,
                        menu_item_id=burger.id,
                        quantity=1,
                        price=burger.price
                    ),
                    OrderItem(
                        order_id=order.id,
                        menu_item_id=fries.id,
                        quantity=1,
                        price=fries.price
                    )
                ]
                
                for item in order_items:
                    db.session.add(item)
        
        db.session.commit()
        
        flash('Test data initialized successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error initializing test data: {str(e)}', 'danger')
    
    return redirect(url_for('home'))
