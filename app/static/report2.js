db.users.aggregate([
    { "$unwind": "$orders" },
    { "$match": { "orders.date_placed": { "$gte": new Date(new Date().setFullYear(new Date().getFullYear() - 1)) } } },
    { "$unwind": "$orders.order_products" },
    {
        "$group": {
            "_id": {
                "product_id": "$orders.order_products.product_id",
                "user_id": "$_id"
            },
            "order_count": { "$sum": 1 }
        }
    },
    { "$match": { "order_count": { "$gte": 2 } } },
    {
        "$group": {
            "_id": "$_id.product_id",
            "multiple_buyer_count": { "$sum": 1 }
        }
    },
    { "$sort": { "multiple_buyer_count": -1, "_id": 1 } },
    {
        "$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "_id",
            "as": "product_details"
        }
    },
    { "$unwind": "$product_details" },
    {
        "$project": {
            "product_id": "$product_details._id",
            "product_name": "$product_details.product_name",
            "multiple_buyer_count": 1
        }
    }
]).pretty()