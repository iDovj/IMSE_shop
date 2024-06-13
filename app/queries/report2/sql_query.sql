WITH order_counts AS (
    SELECT
        op.product_id,
        o.user_id,
        COUNT(op.order_id) AS order_count
    FROM
        order_product op
    JOIN
        "order" o ON op.order_id = o.order_id
    WHERE
        o.date_placed >= NOW() - INTERVAL '1 year'
    GROUP BY
        op.product_id, o.user_id
    HAVING
        COUNT(op.order_id) >= 2
)
SELECT
    p.product_id,
    p.product_name,
    COUNT(oc.user_id) AS multiple_buyer_count
FROM
    product p
JOIN
    order_counts oc ON p.product_id = oc.product_id
GROUP BY
    p.product_id, p.product_name
ORDER BY
    multiple_buyer_count DESC,
    p.product_id ASC;
