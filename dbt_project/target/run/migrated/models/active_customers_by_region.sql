
  
  create view "warehouse"."main"."active_customers_by_region__dbt_tmp" as (
    WITH base AS (
    SELECT
        COALESCE(region, 'Unknown') AS region_val
    FROM "warehouse"."legacy"."customers"
    WHERE is_active = 1
)
SELECT
    MIN(region_val) AS region,
    COUNT(*) AS customer_count
FROM base
GROUP BY LOWER(RTRIM(region_val))
  );
