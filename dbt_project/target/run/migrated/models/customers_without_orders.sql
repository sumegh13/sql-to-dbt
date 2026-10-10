
  
  create view "warehouse"."main"."customers_without_orders__dbt_tmp" as (
    SELECT
    c.customer_id,
    c.customer_name
FROM "warehouse"."legacy"."customers" AS c
WHERE NOT EXISTS (
    SELECT 1
    FROM "warehouse"."legacy"."orders" AS o
    WHERE o.customer_id = c.customer_id
)
  );
