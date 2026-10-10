WITH spend AS (
    SELECT
        customer_id,
        CAST(SUM(amount) AS DECIMAL(38,2)) AS spend
    FROM "warehouse"."legacy"."orders"
    WHERE RTRIM(LOWER(status)) NOT IN ('cancelled', 'returned')
    GROUP BY customer_id
),
joined AS (
    SELECT
        c.customer_id,
        c.customer_name,
        CAST(COALESCE(s.spend, 0) AS DECIMAL(38,2)) AS spend
    FROM "warehouse"."legacy"."customers" c
    LEFT JOIN spend s
        ON s.customer_id = c.customer_id
),
avg_spend AS (
    -- T-SQL AVG over DECIMAL(38,2) keeps scale 2 and truncates the result
    SELECT
        CAST(TRUNC(SUM(spend) * 100 / NULLIF(COUNT(*), 0)) / 100 AS DECIMAL(38,2)) AS avg_spend
    FROM joined
)
SELECT
    j.customer_id,
    j.customer_name,
    j.spend,
    CASE WHEN j.spend > a.avg_spend THEN 'above_avg' ELSE 'at_or_below_avg' END AS vs_avg
FROM joined j
CROSS JOIN avg_spend a