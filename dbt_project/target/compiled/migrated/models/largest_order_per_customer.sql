WITH ranked AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.amount,
        ROW_NUMBER() OVER (
            PARTITION BY o.customer_id
            ORDER BY o.amount DESC NULLS LAST, o.order_id ASC NULLS FIRST
        ) AS rn
    FROM "warehouse"."legacy"."orders" o
    WHERE o.customer_id IS NOT NULL
)
SELECT
    c.customer_id,
    r.order_id,
    r.amount
FROM "warehouse"."legacy"."customers" c
JOIN ranked r
    ON r.customer_id = c.customer_id
   AND r.rn = 1