
  
  create view "warehouse"."main"."largest_order_per_customer__dbt_tmp" as (
    WITH ranked_orders AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.amount,
        ROW_NUMBER() OVER (
            PARTITION BY o.customer_id
            ORDER BY o.amount DESC, o.order_id
        ) AS rn
    FROM "warehouse"."legacy"."orders" o
    WHERE o.customer_id IS NOT NULL
)
SELECT
    c.customer_id,
    r.order_id,
    r.amount
FROM "warehouse"."legacy"."customers" c
INNER JOIN ranked_orders r
    ON r.customer_id = c.customer_id
WHERE r.rn = 1
  );
