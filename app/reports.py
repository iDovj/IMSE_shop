import logging
import time
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import aliased

from .models import User, Order, OrderProduct, Product, Category, Invoice, ProductCategory
from app.main import db

logger = logging.getLogger(__name__)

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
        {"$match": {"orders.date_placed": {"$gte": one_year_ago}}},
        {"$unwind": "$orders"},
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

def log_exec_stats_repeat_buyer_products_no_sql(mongo_db, mongo_client):
     one_year_ago = datetime.utcnow() - timedelta(days=365)

     pipeline = [
         {"$match": {"orders.date_placed": {"$gte": one_year_ago}}},
         {"$unwind": "$orders"},
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

     execution_stats = mongo_db.command(
        'explain',
        {
            'aggregate': "users",
            'pipeline': pipeline,
            'cursor': {}
        },
        verbosity='executionStats'
     )

     execution_time_millis = execution_stats['stages'][0]['$cursor']['executionStats']['executionTimeMillis']

     logger.debug(f"Execution Time Millis: {execution_time_millis}")

def get_users_spending_over_threshold_mongo(mongo_db, threshold):
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    pipeline = [
        {"$match": {"orders.date_placed": {"$gte": six_months_ago}}},
        {"$unwind": "$orders"},
        {"$unwind": "$orders.order_products"},
        {
            "$lookup": {
                "from": "products",
                "localField": "orders.order_products.product_id",
                "foreignField": "_id",
                "as": "product_details"
            }
        },
        {"$unwind": "$product_details"},
        {
            "$group": {
                "_id": {"user_id": "$_id", "product_id": "$orders.order_products.product_id"},
                "total_spent": {"$sum": {"$multiply": ["$orders.order_products.quantity", "$product_details.price"]}}
            }
        },
        {
            "$lookup": {
                "from": "products",
                "localField": "_id.product_id",
                "foreignField": "_id",
                "as": "product_details"
            }
        },
        {"$unwind": "$product_details"},
        {
            "$lookup": {
                "from": "categories",
                "localField": "product_details.category_ids",
                "foreignField": "_id",
                "as": "category_details"
            }
        },
        {"$unwind": "$category_details"},
        {
            "$group": {
                "_id": {"user_id": "$_id.user_id", "category_name": "$category_details.category_name"},
                "total_spent_per_category": {"$sum": "$total_spent"}
            }
        },
        {"$match": {"total_spent_per_category": {"$gt": threshold}}},
        {
            "$project": {
                "user_id": "$_id.user_id",
                "category_name": "$_id.category_name",
                "total_spent_per_category": 1
            }
        },
        {"$sort": {"total_spent_per_category": -1}}
    ]
    
    result = mongo_db['users'].aggregate(pipeline)
    return list(result)

def log_exec_stats_spending_threshold_no_sql(mongo_db, mongo_client, threshold):
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    pipeline = [
        {"$match": {"orders.date_placed": {"$gte": six_months_ago}}},
        {"$unwind": "$orders"},
        {"$lookup": {
            "from": "products",
            "localField": "orders.order_products.product_id",
            "foreignField": "_id",
            "as": "product_details"
        }},
        {"$unwind": "$product_details"},
        {"$unwind": "$orders.order_products"},
        {"$group": {
            "_id": {"user_id": "$_id", "category_name": "$product_details.category_ids"},
            "total_spent_per_category": {"$sum": {"$multiply": ["$orders.order_products.quantity", "$product_details.price"]}}
        }},
        {"$match": {"total_spent_per_category": {"$gt": threshold}}},
        {"$project": {
            "user_id": "$_id.user_id",
            "category_name": "$_id.category_name",
            "total_spent_per_category": 1
        }},
        {"$sort": {"total_spent_per_category": -1}}
    ]
    
    execution_stats = mongo_db.command(
        'explain',
        {
            'aggregate': "users",
            'pipeline': pipeline,
            'cursor': {}
        },
        verbosity='executionStats'
    )

    execution_time_millis = execution_stats['stages'][0]['$cursor']['executionStats']['executionTimeMillis']
    logger.debug(f"Execution Time Millis: {execution_time_millis}")