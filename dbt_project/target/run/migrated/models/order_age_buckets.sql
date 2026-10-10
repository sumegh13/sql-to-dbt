
  
  create view "warehouse"."main"."order_age_buckets__dbt_tmp" as (
    WITH aged AS (
    SELECT
        order_id,
        date_diff('day', order_date, DATE '2025-12-31') AS age_days
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
  );
