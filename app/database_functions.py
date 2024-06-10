import logging
import sys

from sqlalchemy import Numeric

from app.models import Product

logger = logging.getLogger(__name__)

def find_all_products(db, mongo_db, db_status):
    if db_status == 'SQL':
        logger.debug('SQL Products')
        return Product.query.options(db.joinedload(Product.categories)).all()
    elif db_status == 'NO_SQL':
        products_collection = mongo_db['products']
        categories_collection = mongo_db['categories']
        logger.debug('NO SQL Products')
        products = products_collection.find()
        processed_products = []

        for product in products:
            product_dict = {
                "product_id": product["_id"],
                "product_name": product["product_name"],
                "price": str(product["price"].to_decimal()),
                "quantity": product["quantity"],
                "product_desc": product.get("product_desc", ""),
                "categories": []
            }

            for category_id in product.get("category_ids", []):
                category = categories_collection.find_one({"_id": category_id})
                if category:
                    product_dict["categories"].append({
                        "category_name": category["category_name"]
                    })

            processed_products.append(product_dict)

        return processed_products
