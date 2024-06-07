from app import db

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    date_registered = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    orders = db.relationship('Order', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)

class Product(db.Model):
    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_desc = db.Column(db.String(500), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    order_products = db.relationship('OrderProduct', backref='product', lazy=True)

class Order(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    date_placed = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    order_status = db.Column(db.String(50), nullable=False)
    order_products = db.relationship('OrderProduct', backref='order', lazy=True)
    invoice = db.relationship('Invoice', backref='order', uselist=False)

class OrderProduct(db.Model):
    order_product_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    category_desc = db.Column(db.String(500), nullable=True)
    products = db.relationship('Product', backref='category', lazy=True)

class Invoice(db.Model):
    invoice_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    date_issued = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    payment_status = db.Column(db.String(50), nullable=False)

class CartItem(db.Model):
    cart_item_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
