
from app import app, db
from models import Restaurant, MenuItem, Order, OrderItem

def delete_all_restaurants():
    try:
        with app.app_context():
            # First delete all menu items since they reference restaurants
            MenuItem.query.delete()
            
            # Delete all order items and orders
            OrderItem.query.delete()
            Order.query.delete()
            
            # Finally delete all restaurants
            Restaurant.query.delete()
            
            # Commit the changes
            db.session.commit()
            print("Successfully deleted all restaurants and related data.")
        
    except Exception as e:
        print(f"Error deleting restaurants: {str(e)}")

if __name__ == "__main__":
    delete_all_restaurants()
