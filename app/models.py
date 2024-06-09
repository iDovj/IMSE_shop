from sqlalchemy import PrimaryKeyConstraint, Numeric
from app.main import db

# OK
class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(257), nullable=False)
    date_registered = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    orders = db.relationship('Order', back_populates='user', lazy=True)
    cart_products = db.relationship('CartProduct', back_populates='user', lazy=True)

# OK
class Product(db.Model):
    __tablename__ = 'product'
    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(Numeric(precision=10, scale=2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_desc = db.Column(db.String(500), nullable=True)
    categories = db.relationship('Category', secondary='product_category', back_populates='products')
    cart_products = db.relationship('CartProduct', back_populates='product', lazy=True)
    order_products = db.relationship('OrderProduct', back_populates='product', lazy=True)

class Category(db.Model):
    __tablename__ = 'category'
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(100), nullable=False)
    category_desc = db.Column(db.String(500), nullable=True)
    products = db.relationship('Product', secondary='product_category', back_populates='categories')

class ProductCategory(db.Model):
    __tablename__ = 'product_category'
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('product_id', 'category_id'),
    )

# OK
class Accessory(db.Model):
    __tablename__ = 'accessory'
    base_product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    accessory_product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('base_product_id', 'accessory_product_id'),
    )

class Order(db.Model):
    __tablename__ = 'order'
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    date_placed = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    order_status = db.Column(db.String(50), nullable=False)
    order_products = db.relationship('OrderProduct', back_populates='order', lazy=True)
    invoice = db.relationship('Invoice', back_populates='order', cascade='all, delete-orphan', uselist=False)
    user = db.relationship('User', back_populates='orders')

class OrderProduct(db.Model):
    __tablename__ = 'order_product'
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('order_id', 'product_id'),
    )

    order = db.relationship('Order', back_populates='order_products')
    product = db.relationship('Product', back_populates='order_products')

class Invoice(db.Model):
    __tablename__ = 'invoice'
    invoice_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    total_cost = db.Column(Numeric(precision=10, scale=2), nullable=False)  # Using Numeric for precision
    date_issued = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    payment_status = db.Column(db.String(30), nullable=False)

    order = db.relationship('Order', back_populates='invoice')

class CartProduct(db.Model):
    __tablename__ = 'cart_product'
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'product_id'),
    )

    user = db.relationship('User', back_populates='cart_products')
    product = db.relationship('Product', back_populates='cart_products')
