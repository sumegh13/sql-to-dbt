
  
  create view "warehouse"."main"."mom_growth__dbt_tmp" as (
    WITH m AS (
    SELECT
        YEAR(order_date) AS yr,
        MONTH(order_date) AS mo,
        SUM(amount) AS rev
    FROM "warehouse"."legacy"."orders"
    WHERE RTRIM(LOWER(status)) NOT IN ('cancelled', 'returned')
    GROUP BY YEAR(order_date), MONTH(order_date)
),
w AS (
    SELECT
        yr,
        mo,
        rev,
        LAG(rev) OVER (ORDER BY yr, mo) AS prev_rev
    FROM m
)
SELECT
    yr,
    mo,
    rev,
    prev_rev,
    CAST(
        ROUND(
            CAST((rev - prev_rev) AS DECIMAL(38, 10)) * 100.0 / NULLIF(prev_rev, 0),
            2
        ) AS DECIMAL(38, 2)
    ) AS growth_pct
FROM w
  );
