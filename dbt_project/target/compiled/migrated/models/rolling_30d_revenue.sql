WITH d AS (
    SELECT DISTINCT order_date
    FROM "warehouse"."legacy"."orders"
),
valid AS (
    SELECT order_date, amount
    FROM "warehouse"."legacy"."orders"
    WHERE rtrim(lower(status)) NOT IN ('cancelled', 'returned')
)
SELECT
    d.order_date,
    SUM(v.amount) AS rolling_30d
FROM d
LEFT JOIN valid v
    ON v.order_date > d.order_date - 30
   AND v.order_date <= d.order_date
GROUP BY d.order_date