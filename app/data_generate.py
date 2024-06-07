from app import db, create_app
from app.models import User, Product, Category
from faker import Faker
import random

fake = Faker()

app = create_app()

with app.app_context():
    # Generate fake categories
    categories = []
    for _ in range(5):
        category = Category(
            category_name=fake.word(),
            category_desc=fake.text()
        )
        db.session.add(category)
        db.session.commit()
        categories.append(category)

    # Generate fake users
    for _ in range(10):
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            password=fake.password(),
            date_registered=fake.date_this_decade()
        )
        db.session.add(user)

    # Generate fake products
    for _ in range(10):
        product = Product(
            product_name=fake.word(),
            product_desc=fake.text(),
            price=round(random.uniform(5.0, 100.0), 2),
            quantity=random.randint(1, 100),
            category_id=random.choice(categories).category_id
        )
        db.session.add(product)

    db.session.commit()
