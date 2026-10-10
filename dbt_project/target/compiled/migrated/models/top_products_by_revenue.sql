WITH product_revenue AS (
    SELECT
        p.product_id,
        p.product_name,
        CAST(SUM(CAST(i.qty AS DECIMAL(18,2)) * i.unit_price) AS DECIMAL(38,2)) AS revenue
    FROM "warehouse"."legacy"."order_items" i
    JOIN "warehouse"."legacy"."products" p
        ON p.product_id = i.product_id
    GROUP BY p.product_id, p.product_name
)
SELECT
    product_id,
    product_name,
    revenue
FROM product_revenue
ORDER BY revenue DESC, product_id
LIMIT 5