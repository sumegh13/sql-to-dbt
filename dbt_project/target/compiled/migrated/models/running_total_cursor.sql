WITH ordered AS (
    SELECT
        customer_id,
        order_id,
        order_date,
        amount,
        SUM(amount) OVER w AS s,
        COUNT(*) OVER w AS n_all,
        COUNT(amount) OVER w AS n_nonnull
    FROM "warehouse"."legacy"."orders"
    WINDOW w AS (
        PARTITION BY customer_id
        ORDER BY order_date NULLS FIRST, order_id NULLS FIRST
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )
)
SELECT
    customer_id,
    order_id,
    order_date,
    amount,
    CAST(
        CASE
            WHEN customer_id IS NULL THEN amount
            WHEN n_all = n_nonnull THEN s
        END
        AS DECIMAL(18,2)
    ) AS running_total
FROM ordered