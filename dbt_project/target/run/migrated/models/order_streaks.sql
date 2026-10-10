
  
  create view "warehouse"."main"."order_streaks__dbt_tmp" as (
    WITH d AS (
    SELECT DISTINCT customer_id, order_date
    FROM "warehouse"."legacy"."orders"
),
g AS (
    SELECT
        customer_id,
        order_date,
        order_date - CAST(ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS INTEGER) AS grp
    FROM d
)
SELECT
    customer_id,
    MIN(order_date) AS streak_start,
    MAX(order_date) AS streak_end,
    COUNT(*) AS days
FROM g
GROUP BY customer_id, grp
  );
