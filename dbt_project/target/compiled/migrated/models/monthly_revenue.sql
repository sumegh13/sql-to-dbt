SELECT
    CAST(EXTRACT(YEAR FROM order_date) AS INTEGER) AS yr,
    CAST(EXTRACT(MONTH FROM order_date) AS INTEGER) AS mo,
    CAST(SUM(amount) AS DECIMAL(38,2)) AS revenue
FROM "warehouse"."legacy"."orders"
WHERE RTRIM(LOWER(status)) NOT IN ('cancelled', 'returned')
GROUP BY
    EXTRACT(YEAR FROM order_date),
    EXTRACT(MONTH FROM order_date)