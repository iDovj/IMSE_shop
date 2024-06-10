from decimal import Decimal

import pymongo
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload

from app.forms import LoginForm
import sys
import logging

from bson.decimal128 import Decimal128

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db/your_database'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'supersecretkey'

    app.config['DB_STATUS'] = 'not_initialized'

    db.init_app(app)

    return app

app = create_app()
from .models import User, Product, Order, OrderProduct, CartProduct, Invoice, Accessory, Category

# create empty mongo database
mongo_client = pymongo.MongoClient('mongodb://user:password@mongodb:27017/')
mongo_db = mongo_client['mongo_db']

def reset_mongo_db(mongo_db):
    """ function to reset mongodb. just a sanity check to ensure that we don't keep any old data from previous runs. """
    for col_name in mongo_db.list_collection_names():
        mongo_db[col_name].drop()

reset_mongo_db(mongo_db=mongo_db)

def migrate(db, mongo_db):
    session = db.session

    # Migrate User data
    users_collection = mongo_db["users"]
    users = session.query(User).all()
    for user in users:
        user_dict = {
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "password": user.password,
            "date_registered": user.date_registered,
            "orders": [],
            "cart_products": []
        }

        # Add orders
        for order in user.orders:
            order_dict = {
                "order_id": order.order_id,
                "date_placed": order.date_placed,
                "order_status": order.order_status,
                "order_products": [],
                "invoice": {}
            }

            # Add order products
            for order_product in order.order_products:
                order_dict["order_products"].append({
                    "product_id": order_product.product_id,  # Reference to product
                    "quantity": order_product.quantity
                })

            # Add invoice
            if order.invoice:
                invoice = order.invoice
                order_dict["invoice"] = {
                    "invoice_id": invoice.invoice_id,
                    "total_cost": Decimal128(str(invoice.total_cost)),
                    "date_issued": invoice.date_issued,
                    "payment_status": invoice.payment_status
                }

            user_dict["orders"].append(order_dict)

        # Add cart products
        for cart_product in user.cart_products:
            user_dict["cart_products"].append({
                "product_id": cart_product.product_id,  # Reference to product
                "quantity": cart_product.quantity
            })

        users_collection.insert_one(user_dict)

    # Migrate Product data
    products_collection = mongo_db["products"]
    products = session.query(Product).all()
    for product in products:
        product_dict = {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "price": Decimal128(str(product.price)),
            "quantity": product.quantity,
            "product_desc": product.product_desc,
            "category_ids": [category.category_id for category in product.categories],  # References to categories
            "accessory_ids": [accessory.accessory_product_id for accessory in session.query(Accessory).filter_by(base_product_id=product.product_id).all()]  # References to accessories
        }

        products_collection.insert_one(product_dict)

    # Migrate Category data
    categories_collection = mongo_db["categories"]
    categories = session.query(Category).all()
    for category in categories:
        category_dict = {
            "category_id": category.category_id,
            "category_name": category.category_name,
            "category_desc": category.category_desc
        }

        categories_collection.insert_one(category_dict)

    session.close()

# Context processor to inject `logged_in` and `db_status` variables into all templates
@app.context_processor
def inject_db_and_login_status():
    return {
        'logged_in': session.get('logged_in', False),
        'db_status': app.config['DB_STATUS']
    }


@app.route('/')
def reset():
    # Debug statements to check session values
    logger.debug(f"db_status: {session.get('db_status', 'not_initialized')}")
    logger.debug(f"logged_in: {session.get('logged_in', False)}")

    if app.config['DB_STATUS'] == 'not_initialized':
        return redirect(url_for('dashboard'))
    elif session.get('logged_in', False) == False:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('home'))

@app.route('/home')
def home():
    login_form = LoginForm()
    return render_template('home.html', login_form=login_form)

@app.route('/users')
def users():
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/products')
def products():
    all_products = Product.query.options(db.joinedload(Product.categories)).all()
    return render_template('products.html', products=all_products)


@app.route('/orders')
def orders():
    user_id = session.get('user_id')
    if user_id is None:
        flash('You need to be logged in to view your orders.', 'warning')
        return redirect(url_for('login'))

    all_orders = (Order.query.options(joinedload(Order.order_products).joinedload(OrderProduct.product))
                  .order_by(Order.date_placed.desc()).all())
    return render_template('orders.html', orders=all_orders)

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    order = Order.query.get(order_id)
    if order and order.order_status in ['Pending', 'Processing']:
        # Update the product quantities
        for order_product in order.order_products:
            product = order_product.product
            product.quantity += order_product.quantity

        # Change the order status to 'Canceled'
        order.order_status = 'Canceled'
        db.session.commit()
        flash('Order has been canceled and products have been restocked.', 'success')
    else:
        flash('Order cannot be canceled.', 'danger')
    return redirect(url_for('orders'))

@app.route('/logout')
def log_out():
    # user_id = session.get('user_id')
    # if user_id is None:
    #     flash('You need to be logged in to log out.', 'warning')
    #     return redirect(url_for('login'))
    session['user_id'] = None
    session['logged_in'] = False
    flash('Logout successful', 'success')
    return redirect(url_for('reset'))

@app.route('/cart')
def cart():
    user_id = session.get('user_id')
    if user_id is None:
        flash('You need to be logged in to view your cart.', 'warning')
        return redirect(url_for('login'))

    cart_products = CartProduct.query.filter_by(user_id=user_id).all()
    cart = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.product.price} for item in cart_products]
    return render_template('cart.html', cart=cart)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('user_id', 1)  # Temporarily for testing
    quantity = request.form.get('quantity', 1)
    cart_item = CartProduct.query.filter_by(user_id=user_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += int(quantity)
    else:
        cart_item = CartProduct(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    return redirect(url_for('products'))

@app.route('/place_order', methods=['POST'])
def place_order():
    user_id = session.get('user_id', 1)  # Temporarily for testing
    cart_items = CartProduct.query.filter_by(user_id=user_id).all()

    if not cart_items:
        flash("Your cart is empty!", "danger")
        return redirect(url_for('cart'))

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

    CartProduct.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('order_detail', order_id=new_order.order_id))

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_detail.html', order=order)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            logger.debug(f"User found: {user.user_id}")
        else:
            logger.debug(f"No user found")
        if user and password == user.password:
            session['user_id'] = user.user_id
            session['first_name'] = user.first_name
            flash('Login successful', 'success')
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Check email and password', 'danger')
    return render_template('login.html', login_form=form)

@app.route('/dashboard')
def dashboard():
    tables = []
    if session.get('db_status') != 'not_initialized':
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        for table_name in table_names:
            count = db.session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()  # Use text() for raw SQL
            tables.append({'name': table_name, 'entries': count})

    table_count = len(tables)
    return render_template('db_management.html', tables=tables, table_count=table_count)

@app.route('/initialize_db', methods=['POST'])
def initialize_db():
    # Your database initialization logic here
    logger.debug("initialize_db route accessed")
    with app.app_context():
        db.create_all()
        from .data_generation import generate_sample_data
        generate_sample_data(db)
    app.config['DB_STATUS'] = 'SQL'
    # flash('Database initialized successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/report1')
def report1():
    if session.get('db_status') == 'not_initialized':
        flash('Database is not initialized', 'danger')
        return redirect(url_for('dashboard'))
    from app.reports import get_users_spending_over_threshold
    threshold = 1000  # Set threshold value here
    report_data = get_users_spending_over_threshold(threshold)
    return render_template('report1.html', report=report_data)

@app.route('/report2')
def report2():
    if session.get('db_status') == 'not_initialized':
        flash('Database is not initialized', 'danger')
        return redirect(url_for('dashboard'))
    from app.reports import get_repeat_buyer_products
    report_entries = get_repeat_buyer_products()
    return render_template('report2.html', report_entries=report_entries)

@app.route('/copy_to_no_sql')
def copy_to_no_sql():
    logger.debug("copy_to_no_sql route accessed")
    migrate(db, mongo_db)
    app.config['DB_STATUS'] = 'COPIED_TO_NO_SQL'
    # flash('Database copied to NoSQL successfully!', 'success')
    return redirect(url_for('dashboard'))