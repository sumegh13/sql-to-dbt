WITH cal AS (
    SELECT CAST(d AS DATE) AS cal_date
    FROM generate_series(DATE '2025-11-01', DATE '2025-12-31', INTERVAL 1 DAY) AS t(d)
)
SELECT
    c.cal_date,
    CAST(COUNT(o.order_date) AS INTEGER) AS orders_placed
FROM cal c
LEFT JOIN "warehouse"."legacy"."orders" o
    ON o.order_date = c.cal_date
GROUP BY c.cal_date