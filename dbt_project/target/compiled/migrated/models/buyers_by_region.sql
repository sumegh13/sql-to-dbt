WITH buyer_rows AS (
    SELECT c.region, c.customer_id
    FROM "warehouse"."legacy"."customers" c
    INNER JOIN "warehouse"."legacy"."orders" o
        ON o.customer_id = c.customer_id
)
SELECT
    MIN(region) AS region,
    COUNT(DISTINCT customer_id) AS buyers
FROM buyer_rows
GROUP BY UPPER(RTRIM(region))