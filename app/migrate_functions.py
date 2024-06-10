from bson.decimal128 import Decimal128

from app.models import Category, Product, Accessory, User


def reset_mongo_db(mongo_db):
    """Function to reset MongoDB. Just a sanity check to ensure that we don't keep any old data from previous runs."""
    for col_name in mongo_db.list_collection_names():
        mongo_db[col_name].drop()


def migrate(db, mongo_db):
    session = db.session

    # Migrate Category data first
    categories_collection = mongo_db["categories"]
    categories = session.query(Category).all()
    for category in categories:
        category_dict = {
            "_id": category.category_id,  # Use SQL ID as MongoDB _id
            "category_name": category.category_name,
            "category_desc": category.category_desc
        }
        categories_collection.insert_one(category_dict)

    # Migrate Product data next
    products_collection = mongo_db["products"]
    products = session.query(Product).all()
    for product in products:
        product_dict = {
            "_id": product.product_id,  # Use SQL ID as MongoDB _id
            "product_name": product.product_name,
            "price": Decimal128(str(product.price)),
            "quantity": product.quantity,
            "product_desc": product.product_desc,
            "category_ids": [category.category_id for category in product.categories],  # References to categories
            "accessory_ids": [accessory.accessory_product_id for accessory in
                              session.query(Accessory).filter_by(base_product_id=product.product_id).all()]
            # References to accessories
        }
        products_collection.insert_one(product_dict)

    # Migrate User data last
    users_collection = mongo_db["users"]
    users = session.query(User).all()
    for user in users:
        user_dict = {
            "_id": user.user_id,  # Use SQL ID as MongoDB _id
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

    session.close()
