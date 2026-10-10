
  
  create view "warehouse"."main"."customer_first_last_order__dbt_tmp" as (
    WITH ranked AS (
    SELECT
        customer_id,
        FIRST_VALUE(order_id) OVER (
            PARTITION BY customer_id
            ORDER BY order_date NULLS FIRST, order_id NULLS FIRST
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_order,
        LAST_VALUE(order_id) OVER (
            PARTITION BY customer_id
            ORDER BY order_date NULLS FIRST, order_id NULLS FIRST
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_order
    FROM "warehouse"."legacy"."orders"
)
SELECT DISTINCT
    customer_id,
    first_order,
    last_order
FROM ranked
  );
