SELECT
    a.product_id AS product_a,
    b.product_id AS product_b,
    COUNT(DISTINCT a.order_id) AS together
FROM {{ source('legacy', 'order_items') }} AS a
JOIN {{ source('legacy', 'order_items') }} AS b
    ON a.order_id = b.order_id
   AND a.product_id < b.product_id
GROUP BY a.product_id, b.product_id