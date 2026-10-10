
  
  create view "warehouse"."main"."order_outstanding_update_join__dbt_tmp" as (
    WITH pay AS (
    SELECT
        order_id,
        SUM(paid_amount) AS total_paid,
        MAX(paid_date) AS last_dt
    FROM "warehouse"."legacy"."payments"
    GROUP BY order_id
),
base AS (
    SELECT
        o.order_id,
        o.amount,
        CASE
            WHEN p.order_id IS NOT NULL THEN CAST(p.total_paid AS DECIMAL(18,2))
            ELSE CAST(0 AS DECIMAL(18,2))
        END AS paid,
        CAST(p.last_dt AS DATE) AS last_paid
    FROM "warehouse"."legacy"."orders" o
    LEFT JOIN pay p
        ON p.order_id = o.order_id
)
SELECT
    order_id,
    amount,
    paid,
    amount - paid AS outstanding,
    last_paid
FROM base
  );
