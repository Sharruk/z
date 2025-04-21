# EZFOODZ - Food Delivery System

EZFOODZ is a comprehensive food delivery platform that connects customers, restaurant owners, and delivery partners. The system features a modern dark-themed UI, multi-role user support, GPS tracking, real-time order notifications, and a seamless checkout experience.

![EZFOODZ Banner](static/img/banner.png)

## Features

- **Multi-role User System**: Separate interfaces for customers, restaurant owners, and delivery partners
- **Restaurant Discovery**: Browse restaurants with detailed information and menus
- **Interactive Cart**: Add items to cart with real-time notifications
- **Order Management**: Track orders from placement to delivery
- **Restaurant Management**: Restaurant owners can manage menus and track orders
- **Delivery Partner Dashboard**: Delivery partners can accept orders and update delivery status
- **Dark-themed Modern UI**: Sleek, responsive design across all pages

## Test Accounts

You can use the following credentials to test the system:

| Role       | Email                 | Password  |
|------------|----------------------|-----------|
| Customer   | customer@example.com | password  |
| Restaurant | restaurant@example.com | password |
| Delivery   | delivery@example.com | password  |

## Restaurant Management Guide

Restaurant owners can access their dashboard at `/restaurant/dashboard` after logging in with restaurant credentials.

### Restaurant Owner Features:

1. **Toggle Restaurant Status**: Easily switch between open/closed
2. **Menu Management**: 
   - View all menu items
   - Toggle menu item availability
   - Add new menu items (coming soon)
3. **Order Management**:
   - View new orders in real-time
   - Update order status (Preparing → Ready for pickup)
   - View order history
4. **Analytics** (coming soon):
   - Sales performance
   - Popular dishes
   - Customer insights

## Technical Details

- Built with Flask and PostgreSQL
- Authentication using Flask-Login
- Form handling with Flask-WTF
- Responsive UI with Bootstrap 5
- Real-time notifications with JavaScript
- Secure password storage with hashing

## Setup and Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Setup PostgreSQL database with environment variables
4. Run the server: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

## Future Enhancements

- GPS tracking integration
- Payment gateway integration
- Reviews and ratings system
- Push notifications
- Mobile app versions