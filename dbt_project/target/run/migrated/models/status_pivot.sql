
  
  create view "warehouse"."main"."status_pivot__dbt_tmp" as (
    WITH src AS (
    SELECT customer_id, status, order_id
    FROM "warehouse"."legacy"."orders"
)
SELECT
    customer_id,
    COUNT(CASE WHEN RTRIM(LOWER(status)) = 'shipped' THEN order_id END) AS shipped,
    COUNT(CASE WHEN RTRIM(LOWER(status)) = 'pending' THEN order_id END) AS pending,
    COUNT(CASE WHEN RTRIM(LOWER(status)) = 'cancelled' THEN order_id END) AS cancelled
FROM src
GROUP BY customer_id
  );
