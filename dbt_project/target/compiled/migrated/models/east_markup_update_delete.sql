WITH base AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.amount,
        o.status
    FROM "warehouse"."legacy"."orders" o
),
marked AS (
    SELECT
        b.order_id,
        b.customer_id,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM "warehouse"."legacy"."customers" c
                WHERE c.customer_id = b.customer_id
                  AND UPPER(RTRIM(c.region)) = 'EAST'
            )
            THEN CAST(b.amount * 1.1 AS DECIMAL(18, 2))
            ELSE b.amount
        END AS amount,
        b.status
    FROM base b
)
SELECT
    order_id,
    customer_id,
    amount,
    status
FROM marked
WHERE status IS NULL
   OR UPPER(RTRIM(status)) <> 'CANCELLED'