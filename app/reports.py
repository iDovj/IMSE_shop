from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import aliased

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


def get_repeat_buyer_products_sql():
    # Define the one-year interval
    one_year_ago = datetime.now() - timedelta(days=365)

    # Create aliases for the tables
    op = aliased(OrderProduct)
    o = aliased(Order)

    # Subquery to count the orders per product per user in the last year
    subquery = (
        db.session.query(
            op.product_id,
            o.user_id,
            func.count(op.order_id).label('order_count')
        )
        .join(o, op.order_id == o.order_id)
        .filter(o.date_placed >= one_year_ago)
        .group_by(op.product_id, o.user_id)
        .having(func.count(op.order_id) >= 2)
        .subquery()
    )

    # Main query to get the count of users who have ordered the same product more than once
    query = (
        db.session.query(
            Product.product_id,
            Product.product_name,
            func.count(subquery.c.user_id).label('multiple_buyer_count')
        )
        .join(subquery, Product.product_id == subquery.c.product_id)
        .group_by(Product.product_id, Product.product_name)
        .order_by(func.count(subquery.c.user_id).desc(), Product.product_id.asc())
    )

    return query.all()


def get_repeat_buyer_products_no_sql(mongo_db):
    one_year_ago = datetime.utcnow() - timedelta(days=365)

    pipeline = [
        {"$unwind": "$orders"},
        {"$match": {"orders.date_placed": {"$gte": one_year_ago}}},
        {"$unwind": "$orders.order_products"},
        {
            "$group": {
                "_id": {
                    "product_id": "$orders.order_products.product_id",
                    "user_id": "$_id"
                },
                "order_count": {"$sum": 1}
            }
        },
        {"$match": {"order_count": {"$gte": 2}}},
        {
            "$group": {
                "_id": "$_id.product_id",
                "multiple_buyer_count": {"$sum": 1}
            }
        },
        {"$sort": {"multiple_buyer_count": -1, "_id": 1}},
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "_id",
                "as": "product_details"
            }
        },
        {"$unwind": "$product_details"},
        {
            "$project": {
                "product_id": "$product_details._id",
                "product_name": "$product_details.product_name",
                "multiple_buyer_count": 1
            }
        }
    ]

    result = mongo_db['users'].aggregate(pipeline)
    return list(result)