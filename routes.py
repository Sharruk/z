import os
import json
import random
import math
import stripe
from decimal import Decimal
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, func
from app import app, db
from models import User, Restaurant, MenuItem, Order, OrderItem
from utils import allowed_roles
from forms import LoginForm, RegisterForm, CompleteProfileForm

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')



# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    error = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            error = 'Invalid email or password. Please try again.'
        else:
            login_user(user, remember=remember)
            
            # Redirect based on user role
            if user.role == 'restaurant':
                return redirect(url_for('restaurant_dashboard'))
            elif user.role == 'delivery':
                return redirect(url_for('delivery_dashboard'))
            else:
                # Check if profile is complete, if not redirect to complete profile
                if not user.is_profile_complete:
                    return redirect(url_for('complete_profile'))
                return redirect(url_for('user_dashboard'))
    
    return render_template('login.html', error=error, form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegisterForm()
    error = None
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        role = request.form.get('role', 'customer')
        
        # Validate inputs
        if not name or not email or not password:
            error = 'All fields are required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif User.query.filter_by(email=email).first():
            error = 'Email already exists. Please use a different email or login.'
        else:
            # Create new user
            new_user = User(
                username=name,
                email=email,
                phone=phone,
                address=address,
                role=role
            )
            new_user.set_password(password)
            
            # Mark profile as complete if phone and address are provided
            if phone and address:
                new_user.is_profile_complete = True
            
            db.session.add(new_user)
            db.session.commit()
            
            # If user role is restaurant, create restaurant entry
            if role == 'restaurant':
                restaurant = Restaurant(
                    owner_id=new_user.id,
                    name=f"{name}'s Restaurant",
                    address=address or "Address not provided",
                    phone=phone or "Phone not provided"
                )
                db.session.add(restaurant)
                db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html', error=error, form=form)

@app.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    form = CompleteProfileForm()
    error = None
    
    if current_user.is_profile_complete:
        return redirect(url_for('user_dashboard'))
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not phone or not address:
            error = 'Both phone and address are required.'
        else:
            current_user.phone = phone
            current_user.address = address
            current_user.is_profile_complete = True
            db.session.commit()
            
            flash('Profile completed successfully!', 'success')
            return redirect(url_for('user_dashboard'))
    
    return render_template('complete_profile.html', error=error, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear any session data like cart
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Dashboard routes
@app.route('/')
def home():
    restaurants = Restaurant.query.filter_by(is_open=True).all()
    return render_template('home.html', restaurants=restaurants)

@app.route('/dashboard')
@login_required
def user_dashboard():
    if not current_user.is_profile_complete:
        return redirect(url_for('complete_profile'))
    
    if current_user.role == 'restaurant':
        return redirect(url_for('restaurant_dashboard'))
    elif current_user.role == 'delivery':
        return redirect(url_for('delivery_dashboard'))
    
    # For customers
    active_orders = Order.query.filter_by(
        customer_id=current_user.id
    ).filter(
        Order.status.in_(['pending', 'preparing', 'ready', 'picking', 'delivering'])
    ).order_by(Order.created_at.desc()).all()
    
    order_history = Order.query.filter_by(
        customer_id=current_user.id
    ).filter(
        Order.status.in_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('user_dashboard.html', active_orders=active_orders, order_history=order_history)

@app.route('/restaurant/dashboard')
@login_required
@allowed_roles(['restaurant'])
def restaurant_dashboard():
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        flash('Restaurant profile not found. Please contact support.', 'danger')
        return redirect(url_for('home'))
    
    current_orders = Order.query.filter_by(
        restaurant_id=restaurant.id
    ).filter(
        Order.status.in_(['pending', 'preparing', 'ready'])
    ).order_by(Order.created_at.desc()).all()
    
    completed_orders = Order.query.filter_by(
        restaurant_id=restaurant.id
    ).filter(
        Order.status.in_(['completed', 'cancelled'])
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant.id).all()
    
    return render_template(
        'restaurant_dashboard.html', 
        restaurant=restaurant, 
        current_orders=current_orders, 
        completed_orders=completed_orders,
        menu_items=menu_items
    )

@app.route('/delivery/dashboard')
@login_required
@allowed_roles(['delivery'])
def delivery_dashboard():
    # Orders that need a delivery partner
    available_orders = Order.query.filter_by(status='ready').all()
    
    # Orders assigned to this delivery partner
    my_orders = Order.query.filter_by(
        delivery_partner_id=current_user.id
    ).filter(
        Order.status.in_(['picking', 'delivering'])
    ).all()
    
    # Order history
    completed_orders = Order.query.filter_by(
        delivery_partner_id=current_user.id
    ).filter(
        Order.status == 'completed'
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template(
        'delivery_dashboard.html',
        available_orders=available_orders,
        my_orders=my_orders,
        completed_orders=completed_orders
    )

# Restaurant routes
@app.route('/restaurant/<int:restaurant_id>')
def restaurant_details(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    
    return render_template('restaurant_details.html', restaurant=restaurant, menu_items=menu_items)

# Order routes
@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Authorization check - only allow customer, restaurant owner, or assigned delivery partner
    if (current_user.id != order.customer_id and 
        (current_user.role == 'restaurant' and current_user.restaurant_profile.id != order.restaurant_id) and
        current_user.id != order.delivery_partner_id):
        abort(403)
    
    return render_template('order_details.html', order=order)

# Cart routes
@app.route('/add-to-cart', methods=['POST'])
@login_required
@allowed_roles(['customer'])
def add_to_cart():
    if not current_user.is_profile_complete:
        flash('Please complete your profile first.', 'warning')
        return redirect(url_for('complete_profile'))
    
    menu_item_id = request.form.get('menu_item_id')
    quantity = int(request.form.get('quantity', 1))
    
    if not menu_item_id or quantity <= 0:
        flash('Invalid request.', 'danger')
        return redirect(request.referrer)
    
    # Get menu item details
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    
    # Initialize cart if it doesn't exist
    if 'cart' not in session:
        session['cart'] = []
        session['restaurant_id'] = menu_item.restaurant_id
    
    # Check if item is from the same restaurant
    if session.get('restaurant_id') != menu_item.restaurant_id:
        flash('You can only order from one restaurant at a time. Please clear your cart first.', 'warning')
        return redirect(request.referrer)
    
    # Check if item already in cart
    cart = session['cart']
    item_in_cart = False
    
    for item in cart:
        if item['menu_item_id'] == int(menu_item_id):
            item['quantity'] += quantity
            item_in_cart = True
            break
    
    if not item_in_cart:
        # Add new item to cart
        cart.append({
            'menu_item_id': int(menu_item_id),
            'name': menu_item.name,
            'price': menu_item.price,
            'quantity': quantity
        })
    
    session['cart'] = cart
    
    # Set cart notification flag for toast
    session['cart_notification'] = True
    
    # Store the item details in session for display in notification
    session['last_added_item'] = {
        'name': menu_item.name,
        'quantity': quantity,
        'price': menu_item.price
    }
    
    flash(f'Added {quantity} {menu_item.name} to your cart.', 'success')
    
    return redirect(request.referrer)

@app.route('/cart')
@login_required
@allowed_roles(['customer'])
def cart():
    if not session.get('cart'):
        flash('Your cart is empty.', 'info')
        return redirect(url_for('home'))
    
    restaurant_id = session.get('restaurant_id')
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Clear any cart notification data when viewing the cart
    session.pop('cart_notification', None)
    session.pop('last_added_item', None)
    
    # Calculate cart totals
    cart_items = session.get('cart', [])
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    delivery_fee = 40  # Fixed delivery fee
    tax = round(subtotal * 0.05, 2)  # 5% tax
    total = subtotal + delivery_fee + tax
    
    return render_template(
        'cart.html', 
        cart_items=cart_items, 
        restaurant=restaurant,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total
    )

@app.route('/update-cart-item', methods=['POST'])
@login_required
@allowed_roles(['customer'])
def update_cart_item():
    data = request.json
    item_index = data.get('index')
    new_quantity = data.get('quantity')
    
    if item_index is None or new_quantity is None:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    cart = session.get('cart', [])
    
    if item_index < 0 or item_index >= len(cart):
        return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
    
    if new_quantity <= 0:
        # Remove item from cart
        cart.pop(item_index)
    else:
        # Update quantity
        cart[item_index]['quantity'] = new_quantity
    
    session['cart'] = cart
    
    # If cart is empty, remove restaurant_id
    if not cart:
        session.pop('restaurant_id', None)
    
    # Recalculate totals
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    delivery_fee = 40
    tax = round(subtotal * 0.05, 2)
    total = subtotal + delivery_fee + tax
    
    return jsonify({
        'success': True, 
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'cart_count': len(cart)
    })

@app.route('/clear-cart')
@login_required
@allowed_roles(['customer'])
def clear_cart():
    session.pop('cart', None)
    session.pop('restaurant_id', None)
    flash('Cart has been cleared.', 'info')
    return redirect(url_for('home'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
@allowed_roles(['customer'])
def checkout():
    if not session.get('cart'):
        flash('Your cart is empty.', 'info')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'cash')
        delivery_address = request.form.get('delivery_address', current_user.address)
        
        restaurant_id = session.get('restaurant_id')
        cart_items = session.get('cart', [])
        
        # Calculate total
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        delivery_fee = 40  # Fixed delivery fee
        tax = round(subtotal * 0.05, 2)  # 5% tax
        total = subtotal + delivery_fee + tax
        
        # Create order
        order = Order(
            customer_id=current_user.id,
            restaurant_id=restaurant_id,
            total_amount=total,
            delivery_address=delivery_address,
            payment_method=payment_method,
            payment_status='completed' if payment_method == 'online' else 'pending'
        )
        db.session.add(order)
        db.session.flush()  # Get order ID without committing
        
        # Create order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item['menu_item_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        session.pop('restaurant_id', None)
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_details', order_id=order.id))
    
    # GET request
    restaurant_id = session.get('restaurant_id')
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Calculate cart totals
    cart_items = session.get('cart', [])
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    delivery_fee = 40  # Fixed delivery fee
    tax = round(subtotal * 0.05, 2)  # 5% tax
    total = subtotal + delivery_fee + tax
    
    return render_template(
        'checkout.html', 
        cart_items=cart_items, 
        restaurant=restaurant,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total
    )

# API routes
@app.route('/api/search_restaurants')
def search_restaurants():
    query = request.args.get('query', '').lower()
    
    if not query:
        restaurants = Restaurant.query.all()
    else:
        restaurants = Restaurant.query.filter(
            or_(
                Restaurant.name.ilike(f'%{query}%'), 
                Restaurant.cuisine_type.ilike(f'%{query}%'),
                Restaurant.description.ilike(f'%{query}%')
            )
        ).all()
    
    return jsonify({
        'success': True,
        'restaurants': [restaurant.to_dict() for restaurant in restaurants]
    })

@app.route('/api/toggle_restaurant_status', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def toggle_restaurant_status():
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    
    restaurant.is_open = not restaurant.is_open
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_open': restaurant.is_open,
        'message': f'Restaurant is now {"open" if restaurant.is_open else "closed"}'
    })

@app.route('/api/restaurant/upload_image', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def upload_restaurant_image():
    import os
    import uuid
    from werkzeug.utils import secure_filename
    
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
    
    # Ensure upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'success': False, 
            'message': 'Invalid image format. Please upload JPG, PNG, GIF, WEBP, or BMP files.'
        }), 400
    
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    
    try:
        # Create secure unique filename
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"restaurant_{restaurant.id}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Generate public URL
        file_url = f"/static/uploads/{unique_filename}"
        
        # Update restaurant image URL in database
        restaurant.image_url = file_url
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'image_url': file_url
        })
        
    except Exception as e:
        app.logger.error(f"Image upload error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error uploading image: {str(e)}'
        }), 500

@app.route('/api/restaurant/add_menu_item', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def add_menu_item():
    data = request.json
    name = data.get('name')
    price = data.get('price')
    description = data.get('description')
    category = data.get('category')
    is_vegetarian = data.get('is_vegetarian', False)
    
    if not name or not price:
        return jsonify({'success': False, 'message': 'Name and price are required'}), 400
    
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    
    menu_item = MenuItem(
        restaurant_id=restaurant.id,
        name=name,
        description=description,
        price=float(price),
        category=category,
        is_vegetarian=is_vegetarian
    )
    
    db.session.add(menu_item)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Menu item added successfully',
        'item': {
            'id': menu_item.id,
            'name': menu_item.name,
            'price': menu_item.price,
            'description': menu_item.description,
            'category': menu_item.category,
            'is_vegetarian': menu_item.is_vegetarian
        }
    })

@app.route('/api/restaurant/update', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def update_restaurant():
    data = request.json
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
        
    if 'name' in data:
        restaurant.name = data['name']
    if 'description' in data:
        restaurant.description = data['description']
    if 'cuisine_type' in data:
        restaurant.cuisine_type = data['cuisine_type']
    if 'address' in data:
        restaurant.address = data['address']
    if 'phone' in data:
        restaurant.phone = data['phone']
        
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Restaurant details updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/restaurant/update_location', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def update_restaurant_location():
    data = request.json
    location = data.get('location')
    
    if not location:
        return jsonify({'success': False, 'message': 'Location is required'}), 400
    
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    
    restaurant.address = location
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Location updated successfully'
    })

@app.route('/api/order/food_prepared', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def food_prepared():
    data = request.json
    order_id = data.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'message': 'Order ID required'}), 400
        
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    order = Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first()
    
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
        
    order.status = 'ready'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Order marked as ready for pickup'
    })

@app.route('/api/delivery/accept_order', methods=['POST'])
@login_required
@allowed_roles(['delivery'])
def accept_order():
    data = request.json
    order_id = data.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'message': 'Order ID required'}), 400
        
    order = Order.query.filter_by(
        id=order_id,
        status='ready',
        delivery_partner_id=None
    ).first()
    
    if not order:
        return jsonify({'success': False, 'message': 'Order not available'}), 404
        
    order.delivery_partner_id = current_user.id
    order.status = 'picking'
    db.session.commit()
    
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(order.restaurant.address)}"
    
    return jsonify({
        'success': True,
        'message': 'Order accepted successfully',
        'maps_url': maps_url
    })

@app.route('/api/delivery/available_orders')
@login_required
@allowed_roles(['delivery'])
def get_available_orders():
    orders = Order.query.filter_by(
        status='ready',
        delivery_partner_id=None
    ).all()
    
    return jsonify({
        'success': True,
        'orders': [{
            'id': order.id,
            'restaurant_name': order.restaurant.name,
            'restaurant_address': order.restaurant.address,
            'items': order.order_items_display,
            'created_at': order.created_at.isoformat()
        } for order in orders]
    })

@app.route('/api/toggle_menu_item', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def toggle_menu_item():
    data = request.json
    item_id = data.get('item_id')
    
    if not item_id:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Ensure this restaurant belongs to current user
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if menu_item.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    menu_item.is_available = not menu_item.is_available
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_available': menu_item.is_available,
        'message': f'Menu item is now {"available" if menu_item.is_available else "unavailable"}'
    })

@app.route('/api/order/update_status', methods=['POST'])
@login_required
def update_order_status():
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    
    if not order_id or not status:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    order = Order.query.get_or_404(order_id)
    
    # Restaurant marking order as ready
    if current_user.role == 'restaurant':
        restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
        if order.restaurant_id != restaurant.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        if status == 'ready_for_pickup' and order.status == 'preparing':
            order.status = 'ready_for_pickup'
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Order ready for pickup. Notifying delivery partners.'
            })
    
    # Delivery partner accepting order
    elif current_user.role == 'delivery':
        if status == 'picking' and order.status == 'ready_for_pickup':
            if order.delivery_partner_id:
                return jsonify({'success': False, 'message': 'Order already assigned'}), 400
            
            order.delivery_partner_id = current_user.id
            order.status = 'picking'
            db.session.commit()
            
            # Generate restaurant location link
            restaurant = order.restaurant
            maps_link = f"https://www.google.com/maps/dir/?api=1&destination={restaurant.address}"
            
            return jsonify({
                'success': True,
                'message': 'Order assigned successfully',
                'maps_link': maps_link
            })
        
        # Delivery partner picked up order
        elif status == 'delivering' and order.status == 'picking':
            if order.delivery_partner_id != current_user.id:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            
            order.status = 'delivering'
            db.session.commit()
            
            # Generate customer location link
            maps_link = f"https://www.google.com/maps/dir/?api=1&destination={order.delivery_address}"
            
            return jsonify({
                'success': True,
                'message': 'Order picked up, proceed to delivery',
                'maps_link': maps_link
            })
        
        # Mark order as delivered
        elif status == 'completed' and order.status == 'delivering':
            if order.delivery_partner_id != current_user.id:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403
            
            order.status = 'completed'
            order.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Delivery completed successfully'
            })
    
    return jsonify({'success': False, 'message': 'Invalid status transition'}), 400
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')
    
    if not order_id or not status:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    
    order = Order.query.get_or_404(order_id)
    
    # Check authorization
    if current_user.role == 'customer' and current_user.id == order.customer_id:
        # Customers can only cancel pending orders
        if status != 'cancelled' or order.status != 'pending':
            return jsonify({'success': False, 'message': 'Unauthorized action'}), 403
    elif current_user.role == 'restaurant':
        # Restaurant must own this order
        restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
        if order.restaurant_id != restaurant.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Restaurants can only update to certain statuses
        allowed_statuses = {
            'pending': ['preparing', 'cancelled'],
            'preparing': ['ready'],
            'ready': []  # Delivery partner takes over from here
        }
        if status not in allowed_statuses.get(order.status, []):
            return jsonify({'success': False, 'message': 'Invalid status transition'}), 400
    elif current_user.role == 'delivery':
        # Delivery partner must be assigned or taking a ready order
        if order.status == 'ready' and not order.delivery_partner_id:
            # Assign to this delivery partner
            order.delivery_partner_id = current_user.id
            order.status = 'picking'
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Order assigned to you and marked as picking up'
            })
        elif order.delivery_partner_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        # Delivery partners can only update to certain statuses
        allowed_statuses = {
            'picking': ['delivering'],
            'delivering': ['completed']
        }
        if status not in allowed_statuses.get(order.status, []):
            return jsonify({'success': False, 'message': 'Invalid status transition'}), 400
    else:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Update order status
    order.status = status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Order status updated to {status}'
    })

# Delivery Tracking Routes
@app.route('/tracking/<int:order_id>')
@login_required
def tracking(order_id):
    # Get order details
    order = Order.query.get_or_404(order_id)
    
    # Access control: only the customer, restaurant owner, or assigned delivery partner can view
    if (current_user.role == 'customer' and order.customer_id != current_user.id) or \
       (current_user.role == 'restaurant' and order.restaurant.owner_id != current_user.id) or \
       (current_user.role == 'delivery' and order.delivery_partner_id and order.delivery_partner_id != current_user.id):
        flash('You do not have permission to view this order.', 'danger')
        return redirect(url_for('home'))
    
    # For demo purposes, use a public API key or empty string if not available
    maps_api_key = os.environ.get('MAPS_API_KEY', '')
    
    return render_template('delivery_tracking.html', order=order, maps_api_key=maps_api_key)

# Enhanced Delivery Dashboard Route
@app.route('/delivery/enhanced-dashboard')
@login_required
@allowed_roles(['delivery'])
def enhanced_delivery_dashboard():
    # Orders that need a delivery partner
    available_orders = Order.query.filter_by(status='ready').all()
    
    # Orders assigned to this delivery partner
    my_orders = Order.query.filter_by(
        delivery_partner_id=current_user.id
    ).filter(
        Order.status.in_(['picking', 'delivering'])
    ).all()
    
    # Order history
    completed_orders = Order.query.filter_by(
        delivery_partner_id=current_user.id
    ).filter(
        Order.status == 'completed'
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    # Mock data for dashboard (in a real app, this would come from the database)
    total_deliveries = Order.query.filter_by(
        delivery_partner_id=current_user.id,
        status='completed'
    ).count()
    
    # Calculate earnings (10% of order total)
    completed_order_amounts = db.session.query(db.func.sum(Order.total_amount)).filter(
        Order.delivery_partner_id == current_user.id,
        Order.status == 'completed'
    ).scalar() or 0
    
    total_earnings = float(completed_order_amounts) * 0.10
    
    # Mock average rating
    average_rating = 4.7  # In a real app, this would be calculated from ratings
    
    # Check if delivery partner is online
    # In a real app, this would be stored in the user record
    is_online = session.get('delivery_online', False)
    
    return render_template(
        'enhanced_delivery_dashboard.html',
        available_orders=available_orders,
        my_orders=my_orders,
        completed_orders=completed_orders,
        total_deliveries=total_deliveries,
        total_earnings=total_earnings,
        average_rating=average_rating,
        is_online=is_online
    )

# Payment Checkout Route
@app.route('/payment-checkout', methods=['GET', 'POST'])
@login_required
@allowed_roles(['customer'])
def payment_checkout():
    if not session.get('cart'):
        flash('Your cart is empty.', 'info')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'cod')
        delivery_address = request.form.get('delivery_address', current_user.address)
        
        restaurant_id = session.get('restaurant_id')
        cart_items = session.get('cart', [])
        
        # Calculate total
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        delivery_fee = 40  # Fixed delivery fee
        tax = round(subtotal * 0.05, 2)  # 5% tax
        total = subtotal + delivery_fee + tax
        
        # Create order
        order = Order(
            customer_id=current_user.id,
            restaurant_id=restaurant_id,
            total_amount=total,
            delivery_address=delivery_address,
            payment_method=payment_method,
            payment_status='completed' if payment_method != 'cod' else 'pending'
        )
        db.session.add(order)
        db.session.flush()  # Get order ID without committing
        
        # Create order items
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item['menu_item_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        session.pop('restaurant_id', None)
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_details', order_id=order.id))
    
    # GET request
    restaurant_id = session.get('restaurant_id')
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Generate CSRF token for the form
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()
    
    # Create a simple form object with the token
    class SimpleForm:
        def __init__(self, csrf_token):
            self.csrf_token = csrf_token
        
        def hidden_tag(self):
            return f'<input type="hidden" name="csrf_token" value="{self.csrf_token}">'
    
    form = SimpleForm(csrf_token)
    
    # Calculate cart totals
    cart_items = session.get('cart', [])
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    delivery_fee = 40  # Fixed delivery fee
    tax = round(subtotal * 0.05, 2)  # 5% tax
    total = subtotal + delivery_fee + tax
    
    return render_template(
        'payment_checkout.html', 
        cart_items=cart_items, 
        restaurant=restaurant,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total,
        form=form
    )

# Restaurant Bot Route
@app.route('/restaurant/bot')
@login_required
@allowed_roles(['restaurant'])
def restaurant_bot():
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    
    # Get bot settings from session (in a real app, this would come from database)
    bot_settings = session.get('restaurant_bot_settings', {}).get(str(restaurant.id), {
        'bot_enabled': True,
        'auto_accept_orders': True,
        'auto_ready_time': 15
    })
    
    return render_template('restaurant_bot.html', restaurant=restaurant, bot_settings=bot_settings)

# API Routes for Tracking and Location

@app.route('/api/delivery/update_status', methods=['POST'])
@login_required
@allowed_roles(['delivery'])
def update_delivery_status():
    data = request.json
    is_online = data.get('is_online', False)
    
    # In a real app, this would update the database
    # For demo purposes, we'll just use the session
    session['delivery_online'] = is_online
    
    return jsonify({
        'success': True,
        'is_online': is_online
    })

@app.route('/api/delivery/update_location', methods=['POST'])
@login_required
@allowed_roles(['delivery'])
def update_delivery_location():
    data = request.json
    order_id = data.get('order_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not order_id or latitude is None or longitude is None:
        return jsonify({'success': False, 'message': 'Invalid data'}), 400
    
    # Get the order
    order = Order.query.get_or_404(order_id)
    
    # Verify that this delivery partner is assigned to this order
    if order.delivery_partner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # In a real app, you would store this in the database
    # For demo purposes, we'll use the session
    if 'delivery_locations' not in session:
        session['delivery_locations'] = {}
    
    session['delivery_locations'][str(order_id)] = {
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': datetime.now().isoformat()
    }
    
    return jsonify({'success': True})

@app.route('/api/order/<int:order_id>/location')
def get_order_customer_location(order_id):
    # Get the order
    order = Order.query.get_or_404(order_id)
    
    # In a real app, you would geocode the delivery address
    # For demo purposes, we'll generate a random location near Chennai
    # Chennai coordinates: 13.0827° N, 80.2707° E
    base_lat, base_lng = 13.0827, 80.2707
    
    # Generate a random offset (within ~5km)
    lat_offset = random.uniform(-0.05, 0.05)
    lng_offset = random.uniform(-0.05, 0.05)
    
    return jsonify({
        'success': True,
        'latitude': base_lat + lat_offset,
        'longitude': base_lng + lng_offset,
        'address': order.delivery_address
    })

@app.route('/api/order/<int:order_id>/delivery_location')
def get_delivery_location(order_id):
    # Get the order
    order = Order.query.get_or_404(order_id)
    
    # In a real app, this would come from the database
    # For demo purposes, we'll use the session
    delivery_locations = session.get('delivery_locations', {})
    location_data = delivery_locations.get(str(order_id))
    
    if not location_data:
        # If no location data, generate a random location on the path
        # between the restaurant and customer
        base_lat, base_lng = 13.0827, 80.2707  # Chennai coordinates
        lat_offset = random.uniform(-0.03, 0.03)
        lng_offset = random.uniform(-0.03, 0.03)
        
        return jsonify({
            'success': True,
            'latitude': base_lat + lat_offset,
            'longitude': base_lng + lng_offset
        })
    
    return jsonify({
        'success': True,
        'latitude': location_data['latitude'],
        'longitude': location_data['longitude'],
        'last_updated': location_data['timestamp']
    })

# Restaurant Bot Account API
@app.route('/api/restaurant-bot/<int:restaurant_id>/update', methods=['POST'])
@login_required
@allowed_roles(['restaurant'])
def restaurant_bot_update(restaurant_id):
    # Verify ownership
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if restaurant.owner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.json
    bot_enabled = data.get('bot_enabled', False)
    auto_accept_orders = data.get('auto_accept_orders', False)
    auto_ready_time = data.get('auto_ready_time', 15)  # minutes
    
    # In a real app, these settings would be stored in the database
    # For demo purposes, we'll use the session
    if 'restaurant_bot_settings' not in session:
        session['restaurant_bot_settings'] = {}
    
    session['restaurant_bot_settings'][str(restaurant_id)] = {
        'bot_enabled': bot_enabled,
        'auto_accept_orders': auto_accept_orders,
        'auto_ready_time': auto_ready_time
    }
    
    return jsonify({
        'success': True,
        'message': 'Bot settings updated successfully'
    })

# Stripe Checkout Routes
@app.route('/create-checkout-session', methods=['POST'])
@login_required
@allowed_roles(['customer'])
def create_checkout_session():
    if not session.get('cart'):
        flash('Your cart is empty.', 'info')
        return redirect(url_for('home'))
    
    try:
        # Get cart details
        restaurant_id = session.get('restaurant_id')
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        cart_items = session.get('cart', [])
        
        # Calculate cart totals
        subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
        delivery_fee = 40  # Fixed delivery fee
        tax = round(subtotal * 0.05, 2)  # 5% tax
        total = subtotal + delivery_fee + tax
        
        # Prepare line items for Stripe
        line_items = []
        for item in cart_items:
            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': item['name'],
                        'description': f'From {restaurant.name}',
                    },
                    'unit_amount': int(item['price'] * 100),  # Stripe expects amount in cents
                },
                'quantity': item['quantity'],
            })
        
        # Add delivery fee as a separate line item
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': 'Delivery Fee',
                    'description': 'Standard delivery charge',
                },
                'unit_amount': int(delivery_fee * 100),
            },
            'quantity': 1,
        })
        
        # Add tax as a separate line item
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': 'Tax',
                    'description': '5% tax on food items',
                },
                'unit_amount': int(tax * 100),
            },
            'quantity': 1,
        })
        
        # Determine domain for success/cancel URLs
        domain_url = request.host_url.rstrip('/')
        
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=current_user.email,
            success_url=domain_url + '/stripe-success',
            cancel_url=domain_url + '/stripe-cancel',
            metadata={
                'user_id': current_user.id,
                'restaurant_id': restaurant_id,
                'cart_json': json.dumps(cart_items),
                'delivery_address': current_user.address
            }
        )
        
        # Redirect to Stripe's checkout page
        return redirect(checkout_session.url, code=303)
    
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {str(e)}")
        flash('Payment processing error. Please try again.', 'danger')
        return redirect(url_for('cart'))

@app.route('/stripe-success')
@login_required
@allowed_roles(['customer'])
def stripe_success():
    # Create order from cart data
    restaurant_id = session.get('restaurant_id')
    cart_items = session.get('cart', [])
    
    if not cart_items:
        flash('Your order could not be processed. Please try again.', 'warning')
        return redirect(url_for('home'))
    
    # Calculate total
    subtotal = sum(item['price'] * item['quantity'] for item in cart_items)
    delivery_fee = 40  # Fixed delivery fee
    tax = round(subtotal * 0.05, 2)  # 5% tax
    total = subtotal + delivery_fee + tax
    
    # Create order
    order = Order(
        customer_id=current_user.id,
        restaurant_id=restaurant_id,
        total_amount=total,
        delivery_address=current_user.address,
        payment_method='card',
        payment_status='completed'
    )
    db.session.add(order)
    db.session.flush()  # Get order ID without committing
    
    # Create order items
    for item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item['menu_item_id'],
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    session.pop('restaurant_id', None)
    
    # Set success flag for notification
    session['payment_success'] = True
    
    flash('Payment successful! Your order has been placed.', 'success')
    return redirect(url_for('order_details', order_id=order.id))

@app.route('/stripe-cancel')
@login_required
@allowed_roles(['customer'])
def stripe_cancel():
    flash('Payment was cancelled. Your cart has been preserved.', 'warning')
    return redirect(url_for('cart'))

@app.route('/init_db')
def init_db():
    # This route is for testing purposes only
    try:
        # Create test users if they don't exist
        if not User.query.filter_by(email='customer@example.com').first():
            customer = User(
                username='Test Customer',
                email='customer@example.com',
                phone='9876543210',
                address='123 Customer St, City',
                role='customer',
                is_profile_complete=True
            )
            customer.set_password('password')
            db.session.add(customer)
            
        if not User.query.filter_by(email='restaurant@example.com').first():
            restaurant_user = User(
                username='Test Restaurant',
                email='restaurant@example.com',
                phone='9876543211',
                address='456 Restaurant St, City',
                role='restaurant',
                is_profile_complete=True
            )
            restaurant_user.set_password('password')
            db.session.add(restaurant_user)
            
        if not User.query.filter_by(email='delivery@example.com').first():
            delivery = User(
                username='Test Delivery',
                email='delivery@example.com',
                phone='9876543212',
                address='789 Delivery St, City',
                role='delivery',
                is_profile_complete=True
            )
            delivery.set_password('password')
            db.session.add(delivery)
        
        db.session.commit()
        
        # Create restaurants if they don't exist
        restaurant_user = User.query.filter_by(email='restaurant@example.com').first()
        
        if not Restaurant.query.filter_by(name='SSN Main Canteen').first():
            restaurant1 = Restaurant(
                owner_id=restaurant_user.id,
                name='SSN Main Canteen',
                description='The main canteen at SSN College serving a variety of South Indian dishes.',
                cuisine_type='South Indian',
                address='https://maps.app.goo.gl/YevdXRfegZuZS1Wr5',
                phone='9876543211',
                image_url='https://via.placeholder.com/400x200?text=SSN+Main+Canteen',
                rating=4.2,
                is_open=True
            )
            db.session.add(restaurant1)
        
        if not Restaurant.query.filter_by(name="Rishub's Food Court").first():
            restaurant2 = Restaurant(
                owner_id=restaurant_user.id,
                name="Rishub's Food Court",
                description='A modern food court offering a variety of Western dishes and snacks.',
                cuisine_type='Fast Food',
                address='https://maps.app.goo.gl/1HzuQF414hWSorHC9',
                phone='9876543213',
                image_url='https://via.placeholder.com/400x200?text=Rishubs+Food+Court',
                rating=4.5,
                is_open=True
            )
            db.session.add(restaurant2)
            
        if not Restaurant.query.filter_by(name="Ashwin's Food Court").first():
            restaurant3 = Restaurant(
                owner_id=restaurant_user.id,
                name="Ashwin's Food Court",
                description='Authentic North Indian cuisine with a modern twist.',
                cuisine_type='North Indian',
                address='https://maps.app.goo.gl/1ZAjqaWcjAa4Uu5V6',
                phone='9876543214',
                image_url='https://via.placeholder.com/400x200?text=Ashwins+Food+Court',
                rating=4.7,
                is_open=True
            )
            db.session.add(restaurant3)
            
        db.session.commit()
        
        # Add menu items for each restaurant
        restaurant1 = Restaurant.query.filter_by(name='SSN Main Canteen').first()
        restaurant2 = Restaurant.query.filter_by(name="Rishub's Food Court").first()
        restaurant3 = Restaurant.query.filter_by(name="Ashwin's Food Court").first()
        
        # Add menu items for SSN Main Canteen
        if restaurant1 and not MenuItem.query.filter_by(restaurant_id=restaurant1.id).first():
            menu_items1 = [
                MenuItem(restaurant_id=restaurant1.id, name='Dosa', description='Crispy South Indian pancake served with chutney and sambar', price=50, category='Breakfast', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant1.id, name='Idli', description='Steamed rice cakes served with chutney and sambar', price=30, category='Breakfast', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant1.id, name='Pongal', description='Rice and lentil porridge seasoned with pepper, cumin and ghee', price=40, category='Breakfast', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant1.id, name='Lemon Rice', description='Rice flavored with lemon juice, turmeric, and tempering', price=45, category='Lunch', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant1.id, name='Coffee', description='Hot filter coffee, served in traditional style', price=20, category='Beverages', is_vegetarian=True),
            ]
            db.session.add_all(menu_items1)
        
        # Add menu items for Rishub's Food Court
        if restaurant2 and not MenuItem.query.filter_by(restaurant_id=restaurant2.id).first():
            menu_items2 = [
                MenuItem(restaurant_id=restaurant2.id, name='Burger', description='Classic beef burger with lettuce, tomato, and special sauce', price=80, category='Main Course', is_vegetarian=False),
                MenuItem(restaurant_id=restaurant2.id, name='Fries', description='Crispy golden French fries served with ketchup', price=60, category='Sides', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant2.id, name='Coke', description='Refreshing Coca-Cola served with ice', price=40, category='Beverages', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant2.id, name='Sandwich', description='Grilled chicken sandwich with mayo and veggies', price=70, category='Main Course', is_vegetarian=False),
                MenuItem(restaurant_id=restaurant2.id, name='Pasta', description='Creamy pasta with garlic bread on the side', price=100, category='Main Course', is_vegetarian=True),
            ]
            db.session.add_all(menu_items2)
        
        # Add menu items for Ashwin's Food Court
        if restaurant3 and not MenuItem.query.filter_by(restaurant_id=restaurant3.id).first():
            menu_items3 = [
                MenuItem(restaurant_id=restaurant3.id, name='Biryani', description='Fragrant rice dish with tender chicken pieces', price=150, category='Main Course', is_vegetarian=False),
                MenuItem(restaurant_id=restaurant3.id, name='Chicken Curry', description='Spicy chicken curry cooked in traditional style', price=130, category='Main Course', is_vegetarian=False),
                MenuItem(restaurant_id=restaurant3.id, name='Roti', description='Whole wheat flatbread', price=40, category='Bread', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant3.id, name='Paneer Butter Masala', description='Cottage cheese cubes in rich tomato gravy', price=120, category='Main Course', is_vegetarian=True),
                MenuItem(restaurant_id=restaurant3.id, name='Lassi', description='Sweet yogurt-based drink with a hint of cardamom', price=50, category='Beverages', is_vegetarian=True),
            ]
            db.session.add_all(menu_items3)
        
        db.session.commit()
        
        flash('Database initialized with test data!', 'success')
        return redirect(url_for('home'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error initializing database: {str(e)}', 'danger')
        return redirect(url_for('home'))

