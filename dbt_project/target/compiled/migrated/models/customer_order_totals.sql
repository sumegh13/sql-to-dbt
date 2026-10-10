WITH customers_src AS (
    SELECT customer_id, customer_name
    FROM "warehouse"."legacy"."customers"
),
valid_orders AS (
    -- T-SQL: status <> 'cancelled' is case-insensitive, ignores trailing spaces,
    -- and is NULL (excluded) when status is NULL.
    SELECT customer_id, amount
    FROM "warehouse"."legacy"."orders"
    WHERE status IS NOT NULL
      AND UPPER(RTRIM(status)) <> 'CANCELLED'
),
order_agg AS (
    SELECT
        customer_id,
        COUNT(*) AS order_count,
        SUM(amount) AS total_amount
    FROM valid_orders
    GROUP BY customer_id
),
combined AS (
    SELECT
        c.customer_id,
        c.customer_name,
        CAST(COALESCE(a.order_count, 0) AS INTEGER) AS order_count,
        CAST(COALESCE(a.total_amount, 0) AS DECIMAL(18,2)) AS total_amount
    FROM customers_src c
    LEFT JOIN order_agg a
        ON a.customer_id = c.customer_id
)
SELECT
    customer_id,
    customer_name,
    order_count,
    total_amount,
    CASE
        WHEN total_amount >= 1000 THEN 'gold'
        WHEN total_amount >= 500 THEN 'silver'
        ELSE 'bronze'
    END AS tier
FROM combined