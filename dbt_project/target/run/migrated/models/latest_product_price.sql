
  
  create view "warehouse"."main"."latest_product_price__dbt_tmp" as (
    WITH r AS (
  SELECT
    product_id,
    price,
    effective_date,
    ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_date DESC) AS rn
  FROM "warehouse"."legacy"."price_history"
  WHERE effective_date <= DATE '2025-12-31'
)
SELECT
  product_id,
  price,
  effective_date
FROM r
WHERE rn = 1
  );
