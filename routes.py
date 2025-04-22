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

@app.route('/')
def home():
    restaurants = Restaurant.query.filter_by(is_open=True).all()
    return render_template('home.html', restaurants=restaurants)

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

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    data = request.json
    order_id = data.get('order_id')
    status = data.get('status')

    if not order_id or not status:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    order = Order.query.get_or_404(order_id)

    # Restaurant marking order as ready or cancelled
    if current_user.role == 'restaurant':
        restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
        if order.restaurant_id != restaurant.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        # Valid status transitions for restaurant
        valid_transitions = {
            'pending': ['preparing', 'ready', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['cancelled']
        }

        if status not in valid_transitions.get(order.status, []):
            return jsonify({
                'success': False,
                'message': f'Cannot transition from {order.status} to {status}'
            }), 400

        # Update order status
        order.status = status

        # If cancelled, add to order history
        if status == 'cancelled':
            # You might want to add a reason field or additional logging here
            pass

        db.session.commit()

        message = 'Order cancelled successfully' if status == 'cancelled' else 'Order marked as ready for pickup'
        return jsonify({
            'success': True,
            'message': message
        })

    # Delivery partner accepting order
    elif current_user.role == 'delivery':
        if status == 'picking' and order.status == 'ready':
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

@app.route('/restaurant_dashboard')
@login_required
@allowed_roles(['restaurant'])
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