
  
  create view "warehouse"."main"."order_product_list__dbt_tmp" as (
    SELECT
    o.order_id,
    string_agg(p.product_name, ', ' ORDER BY lower(rtrim(p.product_name))) AS products
FROM "warehouse"."legacy"."orders" o
JOIN "warehouse"."legacy"."order_items" i
    ON i.order_id = o.order_id
JOIN "warehouse"."legacy"."products" p
    ON p.product_id = i.product_id
GROUP BY o.order_id
  );
