from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import func

from app.models import User, Product, Category, Order, OrderProduct, ProductCategory, Accessory, CartProduct, Invoice
from mimesis import Generic
import random

def generate_sample_data(db):
    generic = Generic('en')

    # Sample data for categories
    categories_data = [
        {'category_name': 'Electronics', 'category_desc': 'Gadgets and devices'},
        {'category_name': 'Books', 'category_desc': 'Various kinds of books'},
        {'category_name': 'Clothing', 'category_desc': 'Men and Women clothing'},
        {'category_name': 'Home & Kitchen', 'category_desc': 'Home and kitchen appliances'},
        {'category_name': 'Sports', 'category_desc': 'Sporting goods and accessories'},
        {'category_name': 'Toys', 'category_desc': 'Toys for kids and adults'},
        {'category_name': 'Beauty', 'category_desc': 'Beauty and personal care'},
        {'category_name': 'Automotive', 'category_desc': 'Automotive parts and accessories'},
        {'category_name': 'Jewelry', 'category_desc': 'Jewelry and accessories'},
        {'category_name': 'Garden', 'category_desc': 'Garden tools and accessories'},
    ]

    # Populate categories
    category_objects = []
    for cat in categories_data:
        category = Category(
            category_name=cat['category_name'],
            category_desc=cat['category_desc']
        )
        db.session.add(category)
        db.session.commit()
        category_objects.append(category)

    # Helper function to generate realistic prices
    def generate_price():
        return round(np.random.lognormal(mean=5, sigma=1.5), 2)

    # Generate products
    num_products = random.randint(100, 300)
    products = []

    for i in range(num_products):
        product_name = f'Product {i + 1}'
        price = generate_price()
        quantity = random.randint(1, 100)
        product_desc = f'Description for {product_name}'

        product = Product(
            product_name=product_name,
            price=price,
            quantity=quantity,
            product_desc=product_desc
        )
        db.session.add(product)
        db.session.commit()
        products.append(product)

        # Assign categories
        category_choice = random.choices([1, 2, 3], [0.50, 0.35, 0.15])[0]
        assigned_categories = random.sample(category_objects, category_choice)
        for category in assigned_categories:
            product_category = ProductCategory(product_id=product.product_id, category_id=category.category_id)
            db.session.add(product_category)

        db.session.commit()

    # Assign accessories
    for product in products:
        if random.random() < 0.30:  # 30% chance to be an accessory
            base_product = random.choice(products)
            while base_product.product_id == product.product_id:
                base_product = random.choice(products)

            accessory = Accessory(base_product_id=base_product.product_id, accessory_product_id=product.product_id)
            db.session.add(accessory)

            if random.random() < 0.50:  # 50% chance to be an accessory to a second product
                second_base_product = random.choice(products)
                while second_base_product.product_id in [product.product_id, base_product.product_id]:
                    second_base_product = random.choice(products)

                second_accessory = Accessory(base_product_id=second_base_product.product_id,
                                             accessory_product_id=product.product_id)
                db.session.add(second_accessory)

                if random.random() < 0.25:  # 25% chance to be an accessory to a third product
                    third_base_product = random.choice(products)
                    while third_base_product.product_id in [product.product_id, base_product.product_id,
                                                            second_base_product.product_id]:
                        third_base_product = random.choice(products)

                    third_accessory = Accessory(base_product_id=third_base_product.product_id,
                                                accessory_product_id=product.product_id)
                    db.session.add(third_accessory)

            db.session.commit()

    # Filling user
    users = []

    test_user = User(
        first_name='Markus',
        last_name='Schlechttester',
        email='markus.schlechttester@mail.com',
        password='password',
        date_registered=generic.datetime.datetime()
    )
    users.append(test_user)
    db.session.add(test_user)

    for _ in range(9):
        first_name = generic.person.first_name()
        last_name = generic.person.last_name()
        user = User(
            first_name=first_name,
            last_name=last_name,
            email= first_name.lower() + "." + last_name.lower() + "@mail.com",
            password="password",
            date_registered=generic.datetime.datetime()
        )
        users.append(user)
        db.session.add(user)

    db.session.commit()

# more complicated part of filling

    # Sample data for order statuses
    order_status_choices = ['Delivered', 'Canceled', 'Returned']
    order_status_probabilities = [0.70, 0.15, 0.15]

    # Sample data for payment statuses
    payment_status_choices = ['Paid', 'Unpaid']
    payment_status_probabilities = [0.95, 0.05]

    # Helper function to generate random past dates
    def random_past_date(start_years_ago, end_years_ago):
        start_date = datetime.now() - timedelta(days=start_years_ago * 365)
        end_date = datetime.now() - timedelta(days=end_years_ago * 365)
        return start_date + (end_date - start_date) * random.random()

    # Create orders and invoices
    for user in users:
        # Determine the number of orders for the user
        num_orders = random.randint(1, 100)

        # Track purchased products for re-buy logic
        purchased_products = []

        for _ in range(num_orders):
            # Select products for the order
            order_products = set()
            for _ in range(random.randint(1, 5)):
                if random.random() < 0.30 and purchased_products:
                    product = random.choice(purchased_products)
                else:
                    product = random.choice(products)
                    purchased_products.append(product)
                # Ensure no duplicate product in the same order
                while product.product_id in [op.product_id for op in order_products]:
                    product = random.choice(products)
                order_products.add(product)

            # Determine order status
            order_status = random.choices(order_status_choices, order_status_probabilities)[0]

            # Create order
            date_placed = random_past_date(0, 5)
            new_order = Order(
                user_id=user.user_id,
                date_placed=date_placed,
                order_status=order_status
            )
            db.session.add(new_order)
            db.session.commit()

            # Create order products
            total_cost = 0
            for product in order_products:
                quantity = random.randint(1, 5)
                order_product = OrderProduct(
                    order_id=new_order.order_id,
                    product_id=product.product_id,
                    quantity=quantity
                )
                total_cost += product.price * quantity
                db.session.add(order_product)
            db.session.commit()

            # Create invoice
            payment_status = random.choices(payment_status_choices, payment_status_probabilities)[0]
            new_invoice = Invoice(
                order_id=new_order.order_id,
                total_cost=total_cost,
                date_issued=date_placed,
                payment_status=payment_status
            )
            db.session.add(new_invoice)
            db.session.commit()

    # Adjust to ensure 10% of users spent more than 5000 USD in the last 6 months
    six_months_ago = datetime.now() - timedelta(days=180)
    high_spenders = random.sample(users, k=int(0.10 * len(users)))

    for user in high_spenders:
        total_spent_last_6_months = db.session.query(func.sum(Invoice.total_cost)).join(Order).filter(
            Order.user_id == user.user_id,
            Order.date_placed >= six_months_ago
        ).scalar() or 0

        while total_spent_last_6_months < 5000:
            # Create additional orders to meet the spending requirement
            order_products = set(random.sample(products, k=random.randint(1, 5)))
            order_status = random.choices(order_status_choices, order_status_probabilities)[0]
            date_placed = random_past_date(0, 0.5)
            new_order = Order(
                user_id=user.user_id,
                date_placed=date_placed,
                order_status=order_status
            )
            db.session.add(new_order)
            db.session.commit()

            total_cost = 0
            for product in order_products:
                quantity = random.randint(1, 5)
                order_product = OrderProduct(
                    order_id=new_order.order_id,
                    product_id=product.product_id,
                    quantity=quantity
                )
                total_cost += product.price * quantity
                db.session.add(order_product)
            db.session.commit()

            payment_status = random.choices(payment_status_choices, payment_status_probabilities)[0]
            new_invoice = Invoice(
                order_id=new_order.order_id,
                total_cost=total_cost,
                date_issued=date_placed,
                payment_status=payment_status
            )
            db.session.add(new_invoice)
            db.session.commit()

            total_spent_last_6_months += total_cost

    db.session.commit()