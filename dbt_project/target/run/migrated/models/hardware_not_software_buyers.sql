
  
  create view "warehouse"."main"."hardware_not_software_buyers__dbt_tmp" as (
    WITH hardware_buyers AS (
    SELECT DISTINCT o.customer_id
    FROM "warehouse"."legacy"."orders" o
    JOIN "warehouse"."legacy"."order_items" i ON i.order_id = o.order_id
    JOIN "warehouse"."legacy"."products" p ON p.product_id = i.product_id
    WHERE rtrim(lower(p.category)) = 'hardware'
),
software_buyers AS (
    SELECT DISTINCT o.customer_id
    FROM "warehouse"."legacy"."orders" o
    JOIN "warehouse"."legacy"."order_items" i ON i.order_id = o.order_id
    JOIN "warehouse"."legacy"."products" p ON p.product_id = i.product_id
    WHERE rtrim(lower(p.category)) = 'software'
)
SELECT customer_id FROM hardware_buyers
EXCEPT
SELECT customer_id FROM software_buyers
  );
