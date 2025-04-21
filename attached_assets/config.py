import os

class Config:
    """
    Configuration for Flask application
    """
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = True if os.environ.get('FLASK_ENV') == 'development' else False
    
    # Database Settings
    DATABASE_URI = os.environ.get('DATABASE_URI', 'food_delivery.db')
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'dummy-client-id')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'dummy-client-secret')
    
    # Application Settings
    ITEMS_PER_PAGE = 10
    ORDER_STATUSES = ['pending', 'preparing', 'ready', 'picking', 'delivering', 'completed', 'cancelled']
    PAYMENT_STATUSES = ['pending', 'completed', 'failed', 'refunded']


    SQLALCHEMY_DATABASE_URI = 'sqlite:///waitlistpro.db'  # Example for SQLite
    #SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'postgresql://sharruk:12345678@localhost/ezfoodz')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
