WITH base AS (
    SELECT
        item_id,
        order_id,
        qty,
        SUM(CASE WHEN qty IS NULL THEN 1 ELSE 0 END) OVER (
            PARTITION BY order_id
            ORDER BY item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS null_qty_seen,
        SUM(qty) OVER (
            PARTITION BY order_id
            ORDER BY item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS raw_running_qty
    FROM "warehouse"."legacy"."order_items"
),
calc AS (
    SELECT
        item_id,
        order_id,
        qty,
        CASE WHEN null_qty_seen > 0 THEN NULL ELSE CAST(raw_running_qty AS INTEGER) END AS running_qty
    FROM base
)
SELECT
    item_id,
    order_id,
    CAST(qty AS INTEGER) AS qty,
    running_qty,
    CAST(
        CASE
            WHEN running_qty >= 10 THEN 10
            WHEN running_qty >= 5 THEN 5
            ELSE 0
        END
    AS INTEGER) AS discount_pct
FROM calc