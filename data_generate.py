from app.models import User, Product, Category, Order, OrderProduct
from mimesis import Generic
import random

def generate_sample_data(db):
    generic = Generic('en')

    # Создаем категорию еды
    category = Category(
        category_name='Food',
        category_desc='Groceries and food items.'
    )
    db.session.add(category)
    db.session.commit()

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

    # Генерация продуктов с описаниями
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
