from app.models import Product

def find_all_products(db, mongo_db, db_status):
    if db_status == 'SQL':
        return Product.query.options(db.joinedload(Product.categories)).all()
    else:
        return Product.query.options(db.joinedload(Product.categories)).all()
