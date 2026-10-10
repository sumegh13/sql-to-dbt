
  
  create view "warehouse"."main"."status_pivot__dbt_tmp" as (
    WITH src AS (
    SELECT
        customer_id,
        rtrim(lower(status)) AS status_norm,
        order_id
    FROM "warehouse"."legacy"."orders"
)
SELECT
    customer_id,
    CAST(COUNT(CASE WHEN status_norm = 'shipped' THEN order_id END) AS INTEGER) AS shipped,
    CAST(COUNT(CASE WHEN status_norm = 'pending' THEN order_id END) AS INTEGER) AS pending,
    CAST(COUNT(CASE WHEN status_norm = 'cancelled' THEN order_id END) AS INTEGER) AS cancelled
FROM src
GROUP BY customer_id
  );
