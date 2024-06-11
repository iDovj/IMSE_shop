import pymongo
from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload
from app.database_functions import find_all_products, find_all_orders, get_cart, add_item_to_cart, place_new_order, \
    cancel_this_order
from app.models import User, Product, Order, OrderProduct, CartProduct, Invoice, Accessory, Category, db
from app.migrate_functions import migrate, reset_mongo_db
from app.forms import LoginForm
import sys
import logging


# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Suppress pymongo debug messages
logging.getLogger('pymongo').setLevel(logging.INFO)

# Create app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db/your_database'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'
app.config['DB_STATUS'] = 'not_initialized'

# Create SQL DB
db.init_app(app)

# Create mongo DB
mongo_client = pymongo.MongoClient('mongodb://user:password@mongodb:27017/')
mongo_db = mongo_client['mongo_db']
reset_mongo_db(mongo_db=mongo_db)


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
    all_products = find_all_products(db, mongo_db, app.config['DB_STATUS'])
    return render_template('products.html', products=all_products)

@app.route('/orders')
def orders():
    user_id = session.get('user_id')
    if user_id is None:
        flash('You need to be logged in to view your orders.', 'warning')
        return redirect(url_for('login'))

    all_orders = find_all_orders(db, mongo_db, app.config['DB_STATUS'], user_id)
    return render_template('orders.html', orders=all_orders)

@app.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    user_id = session.get('user_id')
    if user_id is None:
        flash('You need to be logged in to cancel an order.', 'warning')
        return redirect(url_for('login'))

    db_status = app.config['DB_STATUS']
    status, message = cancel_this_order(db, mongo_db, db_status, user_id, order_id)
    flash(message, status)
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

    cart = get_cart(db, mongo_db, app.config['DB_STATUS'], user_id)
    return render_template('cart.html', cart=cart)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user_id = session.get('user_id', 1)  # Temporarily for testing
    quantity = request.form.get('quantity', 1)
    add_item_to_cart(db, mongo_db, app.config['DB_STATUS'], user_id, product_id, quantity)
    return redirect(url_for('products'))

@app.route('/place_order', methods=['POST'])
def place_order():
    user_id = session.get('user_id', 1)  # Temporarily for testing
    result = place_new_order(db, mongo_db, app.config['DB_STATUS'], user_id)
    if result["status"] == "error":
        flash(result["message"], "danger")
        return redirect(url_for('cart'))

    flash(result["message"], "success")
    return redirect(url_for('order_detail', order_id=result.get("order_id", 0)))

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    if app.config['DB_STATUS'] == 'SQL':
        order = Order.query.get_or_404(order_id)
        order = {'order_id': order.order_id,
                  'date_placed': order.date_placed,
                  'status': order.order_status,
                 'order_product':
                     [{'product_name': order_product.product.product_name,
                   'quantity': order_product.quantity} for order_product in order.order_products],
                 'invoice':
                     {'total_cost': order.invoice.total_cost}
                 }
    else:
        users_collection = mongo_db['users']
        products_collection = mongo_db['products']
        order = None
        user = users_collection.find_one({"orders.order_id": order_id}, {"orders.$": 1})
        if user and "orders" in user and user["orders"]:
            order = user["orders"][0]
            # Fetch product details for each order_product
            for order_product in order["order_products"]:
                product = products_collection.find_one({"_id": order_product["product_id"]})
                order_product["product_name"] = product["product_name"]
                order_product["price"] = product["price"]
        if not order:
            return "Order not found", 404

    logger.debug(f'New order: {order}')
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

@app.route('/migrate_to_no_sql')
def migrate_to_no_sql():
    logger.debug("migrate_to_no_sql route accessed")
    migrate(db, mongo_db)
    # TODO: drop SQL tables
    app.config['DB_STATUS'] = 'NO_SQL'
    # flash('Database copied to NoSQL successfully!', 'success')
    return redirect(url_for('dashboard'))