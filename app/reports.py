from .models import User, Order, OrderProduct, Product, Category, Invoice, ProductCategory
from app.main import db

def get_users_spending_over_threshold(threshold):
    results = db.session.query(
        User.user_id,
        Category.category_name,
        db.func.sum(Product.price * OrderProduct.quantity).label('total_spent_per_category')
    ).join(Order, User.user_id == Order.user_id
    ).join(OrderProduct, Order.order_id == OrderProduct.order_id
    ).join(Product, OrderProduct.product_id == Product.product_id
    ).join(ProductCategory, Product.product_id == ProductCategory.product_id
    ).join(Category, ProductCategory.category_id == Category.category_id
    ).join(Invoice, Order.order_id == Invoice.order_id
    ).filter(
        Invoice.date_issued >= db.func.now() - db.text("interval '6 months'")
    ).group_by(
        User.user_id,
        Category.category_name
    ).having(
        db.func.sum(Product.price * OrderProduct.quantity) > threshold
    ).order_by(
        db.func.sum(Product.price * OrderProduct.quantity).desc()
    ).all()
    
    return results
