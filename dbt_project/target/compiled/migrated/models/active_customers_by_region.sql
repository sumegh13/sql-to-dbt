WITH active AS (
    SELECT coalesce(region, 'Unknown') AS region_val
    FROM "warehouse"."legacy"."customers"
    WHERE is_active = 1
)
SELECT
    MIN(region_val) AS region,
    COUNT(*) AS customer_count
FROM active
GROUP BY upper(rtrim(region_val))