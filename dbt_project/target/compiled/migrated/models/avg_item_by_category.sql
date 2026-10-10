WITH lines AS (
    SELECT
        p.category,
        CAST(CAST(i.qty AS DECIMAL(18,0)) * CAST(i.unit_price AS DECIMAL(18,2)) AS DECIMAL(38,2)) AS line_value
    FROM "warehouse"."legacy"."order_items" i
    JOIN "warehouse"."legacy"."products" p
        ON p.product_id = i.product_id
),
agg AS (
    SELECT
        LOWER(category) AS category_key,
        MIN(category) AS category,
        SUM(line_value) AS line_sum,
        COUNT(line_value) AS non_null_lines,
        COUNT(*) AS line_count
    FROM lines
    GROUP BY LOWER(category)
)
SELECT
    category,
    CAST(
        (CAST(line_sum * 1000000 AS HUGEINT) // non_null_lines)
        AS DECIMAL(38,6)
    ) / CAST(1000000 AS DECIMAL(38,6)) AS avg_line_value,
    line_count
FROM agg