
  
  create view "warehouse"."main"."inventory_pivot__dbt_tmp" as (
    WITH inv AS (
    SELECT
        product_id,
        RTRIM(UPPER(warehouse)) AS wh,
        qty_on_hand
    FROM "warehouse"."legacy"."inventory"
)
SELECT
    product_id,
    CAST(COALESCE(SUM(CASE WHEN wh = 'A' THEN qty_on_hand END), 0) AS INTEGER) AS wh_a,
    CAST(COALESCE(SUM(CASE WHEN wh = 'B' THEN qty_on_hand END), 0) AS INTEGER) AS wh_b
FROM inv
GROUP BY product_id
  );
