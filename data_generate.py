from mimesis import Generic
from app import db, create_app
from app.models import User, Product, Category
import random

app = create_app()

with app.app_context():
    generic = Generic('en')

    # Создаем категорию еды
    category = Category(
        category_name='Food',
        category_desc='Groceries and food items.'
    )
    db.session.add(category)
    db.session.commit()

    # Генерируем фейковые данные пользователей
    for _ in range(10):
        user = User(
            first_name=generic.person.first_name(),
            last_name=generic.person.last_name(),
            email=generic.person.email(),
            password=generic.person.password(),
            date_registered=generic.datetime.datetime()
        )
        db.session.add(user)

    # Генерируем фейковые данные продуктов питания
    for _ in range(50):  # Создаем 50 продуктов
        product_name = generic.food.dish()
        product_desc = generic.text.text(quantity=1)  # Генерируем описание продукта

        product = Product(
            product_name=product_name,
            product_desc=product_desc,
            price=round(random.uniform(5.0, 100.0), 2),
            quantity=random.randint(1, 100),
            category_id=category.category_id
        )
        db.session.add(product)

    db.session.commit()
