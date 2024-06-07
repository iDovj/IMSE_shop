from app import db
from app.models import User, Product
from app import create_app

def add_data():
    app = create_app()
    with app.app_context():
        user1 = User(first_name='John', last_name='Doe', email='john@example.com', password='password123')
        product1 = Product(name='Product1', description='Description of Product1', price=19.99, quantity=10)
        
        db.session.add(user1)
        db.session.add(product1)
        db.session.commit()

if __name__ == "__main__":
    add_data()
