from mimesis import Person, Text, Food, Datetime, Generic, Hardware, Address
from app import db, create_app
from app.models import User, Product, Category
import random

app = create_app()

with app.app_context():
    person = Person()
    text = Text()
    food = Food()
    datetime = Datetime()
    hardware = Hardware()
    address = Address()

    # Определяем категории товаров
    categories_data = [
        {'category_name': 'Electronics', 'category_desc': 'Gadgets and electronics'},
        {'category_name': 'Clothing', 'category_desc': 'Apparel and accessories'},
        {'category_name': 'Food', 'category_desc': 'Groceries and food items'},
        {'category_name': 'Home & Kitchen', 'category_desc': 'Household and kitchen items'},
        {'category_name': 'Sports & Outdoors', 'category_desc': 'Sports equipment and outdoor gear'}
    ]

    categories = []
    for category_data in categories_data:
        category = Category(
            category_name=category_data['category_name'],
            category_desc=category_data['category_desc']
        )
        db.session.add(category)
        db.session.commit()
        categories.append(category)

    # Генерация пользователей
    for _ in range(10):
        user = User(
            first_name=person.first_name(),
            last_name=person.last_name(),
            email=person.email(),
            password=person.password(),
            date_registered=datetime.datetime()
        )
        db.session.add(user)

    # Генерация продуктов
    for _ in range(10):
        product_name = random.choice([hardware.cpu(), hardware.graphics(), hardware.manufacturer()])
        product = Product(
            product_name=product_name,
            product_desc=text.sentence(),
            price=round(random.uniform(5.0, 100.0), 2),
            quantity=random.randint(1, 100),
            category_id=random.choice(categories).category_id
        )
        db.session.add(product)

    db.session.commit()
