SELECT
    MIN(c.region) AS region,
    QUANTILE_CONT(CAST(o.amount AS DOUBLE), 0.5) AS median_amount
FROM "warehouse"."legacy"."orders" o
JOIN "warehouse"."legacy"."customers" c
    ON c.customer_id = o.customer_id
GROUP BY UPPER(RTRIM(c.region))