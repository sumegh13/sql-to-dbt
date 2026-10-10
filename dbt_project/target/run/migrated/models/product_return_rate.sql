
  
  create view "warehouse"."main"."product_return_rate__dbt_tmp" as (
    WITH joined AS (
    SELECT
        p.product_id,
        p.product_name,
        CASE WHEN rtrim(lower(o.status)) = 'returned' THEN 1 ELSE 0 END AS is_returned
    FROM "warehouse"."legacy"."order_items" i
    JOIN "warehouse"."legacy"."orders" o
        ON o.order_id = i.order_id
    JOIN "warehouse"."legacy"."products" p
        ON p.product_id = i.product_id
)
SELECT
    product_id,
    product_name,
    COUNT(*) AS line_count,
    SUM(is_returned) AS returned_lines,
    CAST(SUM(is_returned) AS DOUBLE) / COUNT(*) AS return_rate
FROM joined
GROUP BY product_id, product_name
  );
