import logging
from datetime import datetime

from bson import Decimal128
from sqlalchemy.orm import joinedload

from app.models import Product, Order, OrderProduct, CartProduct, Invoice

logger = logging.getLogger(__name__)

def find_all_products(db, mongo_db, db_status):
    if db_status == 'SQL':
        logger.debug('SQL Products')
        products = Product.query.options(joinedload(Product.categories)).order_by(Product.product_id.asc()).all()

        # Sorting categories for each product
        for product in products:
            product.categories.sort(key=lambda c: c.category_id)

        return products

    elif db_status == 'NO_SQL':
        products_collection = mongo_db['products']
        categories_collection = mongo_db['categories']
        logger.debug('NO SQL Products')
        products = products_collection.find().sort("_id", 1)  # Sort by _id in ascending order
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

            category_ids = product.get("category_ids", [])
            sorted_category_ids = sorted(category_ids)  # Sort category IDs

            for category_id in sorted_category_ids:
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

        # Sort the products within each order by product_id
        for order in orders:
            order.order_products = sorted(order.order_products, key=lambda x: x.product_id)

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

            # Sort the products within each order by product_id (_id in MongoDB)
            sorted_order_products = sorted(order.get("order_products", []), key=lambda x: x["product_id"])

            for order_product in sorted_order_products:
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


def place_new_order(db, mongo_db, db_status, user_id):
    if db_status == 'SQL':
        cart_items = CartProduct.query.filter_by(user_id=user_id).all()

        if not cart_items:
            return {"status": "error", "message": "Your cart is empty!"}

        new_order = Order(user_id=user_id, order_status='Pending')
        db.session.add(new_order)
        db.session.commit()

        new_order_id = new_order.order_id
        logger.debug(f"New order id: {new_order_id}")

        total_cost = 0
        for item in cart_items:
            order_product = OrderProduct(
                order_id=new_order_id,  # Use the flushed order_id
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.session.add(order_product)
            db.session.commit()

            product = Product.query.get(item.product_id)
            product.quantity -= item.quantity
            total_cost += item.quantity * product.price

        new_invoice = Invoice(order_id=new_order.order_id, total_cost=total_cost, payment_status='Unpaid')
        db.session.add(new_invoice)
        db.session.commit()

        CartProduct.query.filter_by(user_id=user_id).delete()
        db.session.commit()


    elif db_status == 'NO_SQL':
        users_collection = mongo_db['users']
        products_collection = mongo_db['products']
        user = users_collection.find_one({"_id": user_id})

        if not user or not user.get("cart_products"):
            return {"status": "error", "message": "Your cart is empty!"}

        cart_items = user['cart_products']
        total_cost = 0
        order_products = []

        for item in cart_items:
            product = products_collection.find_one({"_id": item["product_id"]})
            if not product:
                continue
            order_products.append({
                "product_id": product["_id"],
                "quantity": item["quantity"],
                "product_name": product["product_name"],
                "price": product["price"]
            })
            products_collection.update_one(
                {"_id": product["_id"]},
                {"$inc": {"quantity": -item["quantity"]}}
            )

            total_cost += item["quantity"] * float(product["price"].to_decimal())

        # Calculate the new order ID by looking at all order IDs from all users
        all_users = users_collection.find()
        max_order_id = 0

        for user in all_users:
            for order in user.get("orders", []):
                if order["order_id"] > max_order_id:
                    max_order_id = order["order_id"]

        logger.debug(f"Max order id: {max_order_id}")
        new_order_id = max_order_id + 1
        new_order = {
            "order_id": new_order_id,
            "date_placed": datetime.utcnow(),
            "order_status": 'Pending',
            "order_products": order_products,
            "invoice": {
                "invoice_id": new_order_id,  # Using the same ID for simplicity
                "total_cost": Decimal128(str(total_cost)),
                "date_issued": datetime.utcnow(),
                "payment_status": 'Unpaid'
            }
        }

        users_collection.update_one(
            {"_id": user_id},
            {
                "$push": {"orders": new_order},
                "$set": {"cart_products": []}  # Clear the cart after placing the order
            }
        )

    return {"status": "success", "message": "Order placed successfully!", "order_id": new_order_id}

def cancel_this_order(db, mongo_db, db_status, user_id, order_id):
    if db_status == 'SQL':
        order = Order.query.get(order_id)
        if order and order.order_status in ['Pending', 'Processing']:
            # Update the product quantities
            for order_product in order.order_products:
                product = order_product.product
                product.quantity += order_product.quantity

            # Change the order status to 'Canceled'
            order.order_status = 'Canceled'
            db.session.commit()
            return 'success', 'Order has been canceled and products have been restocked.'
        else:
            return 'danger', 'Order cannot be canceled.'

    elif db_status == 'NO_SQL':
        users_collection = mongo_db['users']
        products_collection = mongo_db['products']

        # Find the user containing the order
        user = users_collection.find_one({"_id": user_id})
        if user:
            order = next((order for order in user['orders'] if order['order_id'] == order_id), None)
            if order and order['order_status'] in ['Pending', 'Processing']:
                # Update the product quantities
                for order_product in order['order_products']:
                    product_id = order_product['product_id']
                    quantity = order_product['quantity']
                    products_collection.update_one({"_id": product_id}, {"$inc": {"quantity": quantity}})

                # Change the order status to 'Canceled'
                users_collection.update_one(
                    {"_id": user_id, "orders.order_id": order_id},
                    {"$set": {"orders.$.order_status": 'Canceled'}}
                )
                return 'success', 'Order has been canceled and products have been restocked.'
            else:
                return 'danger', 'Order cannot be canceled.'
        else:
            return 'danger', 'Order cannot be found.'

    return 'danger', 'Unknown database status.'