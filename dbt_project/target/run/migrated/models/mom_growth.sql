
  
  create view "warehouse"."main"."mom_growth__dbt_tmp" as (
    WITH m AS (
    SELECT
        CAST(year(order_date) AS INTEGER) AS yr,
        CAST(month(order_date) AS INTEGER) AS mo,
        SUM(amount) AS rev
    FROM "warehouse"."legacy"."orders"
    WHERE rtrim(lower(status)) NOT IN ('cancelled', 'returned')
    GROUP BY year(order_date), month(order_date)
),
s AS (
    SELECT
        yr,
        mo,
        rev,
        LAG(rev) OVER (ORDER BY yr NULLS FIRST, mo NULLS FIRST) AS prev_rev
    FROM m
)
SELECT
    yr,
    mo,
    rev,
    prev_rev,
    ROUND(CAST(rev - prev_rev AS DECIMAL(38, 10)) * 100.0 / NULLIF(prev_rev, 0), 2) AS growth_pct
FROM s
  );
