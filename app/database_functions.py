import logging

from sqlalchemy.orm import joinedload

from app.models import Product, Order, OrderProduct, CartProduct

logger = logging.getLogger(__name__)

def find_all_products(db, mongo_db, db_status):
    if db_status == 'SQL':
        logger.debug('SQL Products')
        return Product.query.options(joinedload(Product.categories)).all()
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


def find_all_orders(db, mongo_db, db_status, user_id):
    if db_status == 'SQL':
        logger.debug('SQL Orders')
        orders = (Order.query.options(joinedload(Order.order_products).joinedload(OrderProduct.product))
                  .filter(Order.user_id == user_id)
                  .order_by(Order.date_placed.desc())
                  .all())
        return orders

    elif db_status == 'NO_SQL':
        logger.debug('NO SQL Orders')
        users_collection = mongo_db['users']
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return []

        processed_orders = []

        # Sort orders by date_placed descending
        sorted_orders = sorted(user.get("orders", []), key=lambda x: x["date_placed"], reverse=True)

        for order in sorted_orders:
            order_dict = {
                "order_id": order["order_id"],
                "date_placed": order["date_placed"],
                "order_status": order["order_status"],
                "order_products": [],
                "invoice": order.get("invoice", {})
            }

            for order_product in order.get("order_products", []):
                product = mongo_db['products'].find_one({"_id": order_product["product_id"]})
                if product:
                    order_product_dict = {
                        "product": {
                            "product_name": product["product_name"],
                            "price": str(product["price"].to_decimal())  # Convert Decimal128 to string
                        },
                        "quantity": order_product["quantity"]
                    }
                    order_dict["order_products"].append(order_product_dict)

            processed_orders.append(order_dict)

        return processed_orders

def get_cart(db, mongo_db, db_status, user_id):
    if db_status == "SQL":
        logger.debug('SQL Cart')
        cart_products = CartProduct.query.filter_by(user_id=user_id).all()
        cart = [{'product_name': item.product.product_name, 'quantity': item.quantity, 'price': item.product.price} for
                item in cart_products]
        return cart
    elif db_status == "NO_SQL":
        logger.debug('NO SQL Cart')
        users_collection = mongo_db['users']
        products_collection = mongo_db['products']
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return []

        cart_products = []
        for cart_item in user.get("cart_products", []):
            product = products_collection.find_one({"_id": cart_item["product_id"]})
            if product:
                cart_products.append({
                    "product_name": product["product_name"],
                    "price": str(product["price"].to_decimal()),  # Convert Decimal128 to string
                    "quantity": cart_item["quantity"]
                })

        return cart_products

def add_item_to_cart(db, mongo_db, db_status, user_id, product_id, quantity):
    if db_status == 'SQL':
        logger.debug('SQL Add item to cart')
        cart_item = CartProduct.query.filter_by(user_id=user_id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += int(quantity)
        else:
            cart_item = CartProduct(user_id=user_id, product_id=product_id, quantity=quantity)
            db.session.add(cart_item)
        db.session.commit()
    elif db_status == 'NO_SQL':
        logger.debug('NO SQL Add item to cart')
        users_collection = mongo_db['users']
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return

        updated = False
        for item in user.get('cart_products', []):
            if item['product_id'] == product_id:
                item['quantity'] += int(quantity)
                updated = True
                break

        if not updated:
            user.setdefault('cart_products', []).append({
                'product_id': product_id,
                'quantity': int(quantity)
            })

        users_collection.update_one({"_id": user_id}, {"$set": {"cart_products": user['cart_products']}})
