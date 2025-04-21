# Additional routes to be added to routes.py

# Add these imports at the top of routes.py
from flask import redirect, render_template, url_for, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import json
import random
from decimal import Decimal
import math

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

# Restaurant Bot Status
@app.route('/api/restaurant-bot/<int:restaurant_id>/status')
@login_required
@allowed_roles(['restaurant'])
def restaurant_bot_status(restaurant_id):
    # Verify ownership
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if restaurant.owner_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Get bot settings from session
    bot_settings = session.get('restaurant_bot_settings', {}).get(str(restaurant_id), {
        'bot_enabled': False,
        'auto_accept_orders': False,
        'auto_ready_time': 15
    })
    
    # Get recent orders processed by bot
    pending_orders = Order.query.filter_by(
        restaurant_id=restaurant_id,
        status='pending'
    ).count()
    
    preparing_orders = Order.query.filter_by(
        restaurant_id=restaurant_id,
        status='preparing'
    ).count()
    
    # In a real app, you would have a log of bot actions
    # For demo purposes, we'll generate some mock data
    bot_actions = []
    if bot_settings['bot_enabled']:
        action_types = ['order_accepted', 'order_prepared', 'customer_notified']
        for i in range(3):
            action_type = random.choice(action_types)
            time_ago = random.randint(5, 60)
            bot_actions.append({
                'type': action_type,
                'time': (datetime.now() - timedelta(minutes=time_ago)).isoformat(),
                'details': f'Order #{random.randint(1000, 9999)}'
            })
    
    return jsonify({
        'success': True,
        'settings': bot_settings,
        'stats': {
            'pending_orders': pending_orders,
            'preparing_orders': preparing_orders,
            'orders_processed_today': random.randint(10, 50),
            'average_processing_time': random.randint(10, 20)
        },
        'recent_actions': bot_actions
    })