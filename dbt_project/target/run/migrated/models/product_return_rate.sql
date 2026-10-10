
  
  create view "warehouse"."main"."product_return_rate__dbt_tmp" as (
    WITH line_status AS (
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
    CAST(COUNT(*) AS INTEGER) AS line_count,
    CAST(SUM(is_returned) AS INTEGER) AS returned_lines,
    CAST(SUM(is_returned) AS DOUBLE) / COUNT(*) AS return_rate
FROM line_status
GROUP BY product_id, product_name
  );
