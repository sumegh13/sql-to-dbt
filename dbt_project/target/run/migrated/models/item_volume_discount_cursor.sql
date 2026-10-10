
  
  create view "warehouse"."main"."item_volume_discount_cursor__dbt_tmp" as (
    WITH base AS (
    SELECT
        item_id,
        order_id,
        qty,
        SUM(qty) OVER (
            PARTITION BY order_id
            ORDER BY item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS run_sum,
        COUNT(*) OVER (
            PARTITION BY order_id
            ORDER BY item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) - COUNT(qty) OVER (
            PARTITION BY order_id
            ORDER BY item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS null_qty_so_far
    FROM "warehouse"."legacy"."order_items"
)
SELECT
    item_id,
    order_id,
    qty,
    CAST(CASE WHEN null_qty_so_far > 0 THEN NULL ELSE run_sum END AS INTEGER) AS running_qty,
    CAST(
        CASE
            WHEN null_qty_so_far > 0 THEN 0
            WHEN run_sum >= 10 THEN 10
            WHEN run_sum >= 5 THEN 5
            ELSE 0
        END
    AS INTEGER) AS discount_pct
FROM base
  );
