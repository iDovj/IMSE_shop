import time
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from .forms import RegistrationForm, LoginForm


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
from .models import User, Product, Order, OrderProduct, CartItem, Category, Invoice

@app.context_processor
def inject_forms():
    return dict(register_form=RegistrationForm(), login_form=LoginForm())

@app.route('/')
def home():
    register_form = RegistrationForm()
    login_form = LoginForm()
    return render_template('home.html', register_form=register_form, login_form=login_form)


@app.route('/users')
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/products')
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)

@app.route('/cart')
def cart():
    user_id = session.get('user_id', 1)  # Временно для тестов
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    cart = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.product.price} for item in cart_items]
    return render_template('cart.html', cart=cart)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
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
    from .data_generate import generate_sample_data
    generate_sample_data(db)
    return redirect(url_for('home'))

@app.route('/report_d')
def report_d():
    from .reports import get_users_spending_over_threshold
    threshold = 1000  # Здесь можно установить пороговое значение
    report_data = get_users_spending_over_threshold(threshold)
    print("Report Data:", report_data)
    return render_template('report_d.html', report=report_data)

@app.route('/register', methods=['POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already registered')
            return redirect(url_for('home'))

        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        flash('You have successfully registered')
        return redirect(url_for('home'))
    return render_template('home.html', register_form=form, login_form=LoginForm())


@app.route('/login', methods=['POST'])
def login():
    from app.models import User
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            flash('Login successful')
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Check email and password')
    return render_template('home.html', register_form=RegistrationForm(), login_form=form)
