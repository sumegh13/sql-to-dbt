WITH aged AS (
    SELECT
        order_id,
        CAST(DATE '2025-12-31' - order_date AS INTEGER) AS age_days
    FROM "warehouse"."legacy"."orders"
)
SELECT
    order_id,
    age_days,
    CASE
        WHEN age_days <= 30 THEN '0-30'
        WHEN age_days <= 90 THEN '31-90'
        ELSE '90+'
    END AS bucket
FROM aged