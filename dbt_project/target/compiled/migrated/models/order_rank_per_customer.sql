SELECT
    order_id,
    customer_id,
    amount,
    ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY amount DESC NULLS LAST, order_id ASC NULLS FIRST
    ) AS rn,
    RANK() OVER (
        PARTITION BY customer_id
        ORDER BY amount DESC NULLS LAST
    ) AS rnk,
    DENSE_RANK() OVER (
        PARTITION BY customer_id
        ORDER BY amount DESC NULLS LAST
    ) AS drnk
FROM "warehouse"."legacy"."orders"