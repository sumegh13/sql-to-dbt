SELECT
    c.customer_id,
    c.customer_name
FROM "warehouse"."legacy"."customers" c
WHERE NOT EXISTS (
    SELECT 1
    FROM "warehouse"."legacy"."orders" o
    WHERE o.customer_id = c.customer_id
)