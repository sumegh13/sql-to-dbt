WITH spend AS (
    SELECT
        customer_id,
        SUM(amount) AS spend
    FROM "warehouse"."legacy"."orders"
    WHERE rtrim(lower(status)) NOT IN ('cancelled', 'returned')
    GROUP BY customer_id
),
joined AS (
    SELECT
        c.customer_id,
        c.customer_name,
        COALESCE(s.spend, 0) AS spend
    FROM "warehouse"."legacy"."customers" c
    LEFT JOIN spend s
        ON s.customer_id = c.customer_id
),
flagged AS (
    SELECT
        customer_id,
        customer_name,
        spend,
        spend * COUNT(*) OVER () > SUM(spend) OVER () AS is_above
    FROM joined
)
SELECT
    customer_id,
    customer_name,
    spend,
    CASE WHEN is_above THEN 'above_avg' ELSE 'at_or_below_avg' END AS vs_avg
FROM flagged