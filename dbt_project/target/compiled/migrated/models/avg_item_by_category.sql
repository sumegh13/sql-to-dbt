WITH base AS (
    SELECT p.category, i.qty, i.unit_price
    FROM "warehouse"."legacy"."order_items" i
    JOIN "warehouse"."legacy"."products" p ON p.product_id = i.product_id
),
agg AS (
    SELECT
        MIN(category) AS category,
        SUM(CAST(ROUND(qty * unit_price * 100) AS HUGEINT)) AS total_cents,
        COUNT(qty * unit_price) AS n_nonnull,
        COUNT(*) AS line_count
    FROM base
    GROUP BY LOWER(RTRIM(category))
),
calc AS (
    SELECT
        category,
        CASE
            WHEN n_nonnull > 0
            THEN (total_cents * 10000) // n_nonnull
            ELSE NULL
        END AS avg_micro,
        line_count
    FROM agg
)
SELECT
    category,
    CAST(CAST(avg_micro AS DECIMAL(38,6)) / CAST(1000000 AS DECIMAL(38,6)) AS DECIMAL(38,6)) AS avg_line_value,
    line_count
FROM calc