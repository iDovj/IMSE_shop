WITH user_category_spending AS (
    SELECT
        u.user_id,
        c.category_name,
        SUM(p.price * op.quantity) AS total_spent
    FROM
        "user" u
    JOIN
        "order" o ON u.user_id = o.user_id
    JOIN
        order_product op ON o.order_id = op.order_id
    JOIN
        product p ON op.product_id = p.product_id
    JOIN
        product_category pc ON p.product_id = pc.product_id
    JOIN
        category c ON pc.category_id = c.category_id
    JOIN
        invoice i ON o.order_id = i.order_id
    WHERE
        i.date_issued >= NOW() - INTERVAL '6 months'
    GROUP BY
        u.user_id, c.category_name
)
SELECT
    user_id,
    category_name,
    total_spent
FROM
    user_category_spending
WHERE
    total_spent > 5000
ORDER BY
    total_spent DESC;
