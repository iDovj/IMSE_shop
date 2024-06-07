import time
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db/your_database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'supersecretkey'

    db.init_app(app)
    from .models import User, Product, Order, OrderProduct, CartItem, Category, Invoice

    with app.app_context():
        time.sleep(10)  # Задержка перед подключением к базе данных
        db.create_all()

    return app

app = create_app()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/users')
def users():
    from .models import User
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/products')
def products():
    from .models import Product
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)

@app.route('/cart')
def cart():
    from .models import CartItem, Product
    user_id = session.get('user_id', 1)  # Временно для тестов
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    cart = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.product.price} for item in cart_items]
    return render_template('cart.html', cart=cart)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    from .models import CartItem
    user_id = session.get('user_id', 1)  # Временно для тестов
    quantity = request.form.get('quantity', 1)
    cart_item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += int(quantity)
    else:
        cart_item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    return redirect(url_for('products'))

@app.route('/place_order', methods=['POST'])
def place_order():
    from .models import Order, OrderProduct, Product, CartItem, Invoice
    user_id = session.get('user_id', 1)  # Временно для тестов
    cart_items = CartItem.query.filter_by(user_id=user_id).all()

    if not cart_items:
        return "Your cart is empty!", 400

    new_order = Order(user_id=user_id, order_status='Pending')
    db.session.add(new_order)
    db.session.commit()

    total_cost = 0
    for item in cart_items:
        order_product = OrderProduct(
            order_id=new_order.order_id,
            product_id=item.product_id,
            quantity=item.quantity
        )
        db.session.add(order_product)

        product = Product.query.get(item.product_id)
        product.quantity -= item.quantity
        total_cost += item.quantity * product.price
        db.session.commit()

    new_invoice = Invoice(order_id=new_order.order_id, total_cost=total_cost, payment_status='Paid')
    db.session.add(new_invoice)
    db.session.commit()

    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return "Order placed successfully!"

@app.route('/fill_db', methods=['POST'])
def fill_db():
    from .models import User, Product, Category
    from faker import Faker
    import random

    fake = Faker()

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

    return redirect(url_for('home'))

@app.route('/report_d')
def report_d():
    from .reports import get_users_spending_over_threshold
    threshold = 1000  # Здесь можно установить пороговое значение
    report_data = get_users_spending_over_threshold(threshold)
    print("Report Data:", report_data)
    return render_template('report_d.html', report=report_data)
