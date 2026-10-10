WITH d AS (
    SELECT DISTINCT order_date
    FROM "warehouse"."legacy"."orders"
)
SELECT
    d.order_date,
    (
        SELECT SUM(o2.amount)
        FROM "warehouse"."legacy"."orders" o2
        WHERE o2.order_date > d.order_date - 30
          AND o2.order_date <= d.order_date
          AND RTRIM(LOWER(o2.status)) NOT IN ('cancelled', 'returned')
    ) AS rolling_30d
FROM d