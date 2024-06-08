from datetime import datetime

from app.models import User, Product, Category, Order, OrderProduct
from mimesis import Generic
import random

def generate_sample_data(db):
    generic = Generic('en')

    # Список категорий из JSON
    categories_data = [
        {'category_name': 'Dishes', 'category_desc': 'Various dishes from around the world.'},
        {'category_name': 'Drinks', 'category_desc': 'Beverages and drinks.'},
        {'category_name': 'Fruits', 'category_desc': 'All kinds of fruits.'},
        {'category_name': 'Spices', 'category_desc': 'Various spices.'},
        {'category_name': 'Vegetables', 'category_desc': 'All kinds of vegetables.'}
    ]

    category_objects = []

    for cat in categories_data:
        category = Category(
            category_name=cat['category_name'],
            category_desc=cat['category_desc']
        )
        db.session.add(category)
        db.session.commit()
        category_objects.append(category)

    # Генерация фейковых данных пользователей
    for _ in range(10):
        user = User(
            first_name=generic.person.first_name(),
            last_name=generic.person.last_name(),
            email=generic.person.email(),
            password=generic.person.password(),
            date_registered=generic.datetime.datetime()
        )
        db.session.add(user)

    test_user = User(
        first_name='Markus',
        last_name='Schlechttester',
        email='test@mail.com',
        password='test',
        date_registered=datetime(1,1,1)
    )

    db.session.add(test_user)

    # Генерация продуктов с описаниями для каждой категории
    for category in category_objects:
        for _ in range(10):
            product_name = generic.food.dish()
            product_desc = generic.text.sentence()
            product = Product(
                product_name=product_name,
                product_desc=product_desc,
                price=round(random.uniform(5.0, 100.0), 2),
                quantity=random.randint(1, 100),
                category_id=category.category_id
            )
            db.session.add(product)

    db.session.commit()
