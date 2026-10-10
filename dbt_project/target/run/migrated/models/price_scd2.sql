
  
  create view "warehouse"."main"."price_scd2__dbt_tmp" as (
    WITH src AS (
    SELECT
        product_id,
        price,
        effective_date,
        LEAD(effective_date) OVER (
            PARTITION BY product_id
            ORDER BY effective_date NULLS FIRST
        ) AS next_effective
    FROM "warehouse"."legacy"."price_history"
)
SELECT
    product_id,
    price,
    effective_date AS valid_from,
    COALESCE(next_effective, DATE '9999-12-31') AS valid_to,
    CASE WHEN next_effective IS NULL THEN 1 ELSE 0 END AS is_current
FROM src
  );
