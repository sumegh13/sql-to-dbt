
  
  create view "warehouse"."main"."repeat_purchase_flag__dbt_tmp" as (
    WITH base AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        LAG(order_date) OVER (
            PARTITION BY customer_id
            ORDER BY order_date, order_id
        ) AS prev_date
    FROM "warehouse"."legacy"."orders"
)
SELECT
    order_id,
    customer_id,
    order_date,
    prev_date,
    CASE
        WHEN date_diff('day', prev_date, order_date) <= 7 THEN 1
        ELSE 0
    END AS is_repeat_7d
FROM base
  );
