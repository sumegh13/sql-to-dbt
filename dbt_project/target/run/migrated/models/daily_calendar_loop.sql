
  
  create view "warehouse"."main"."daily_calendar_loop__dbt_tmp" as (
    WITH cal AS (
    SELECT CAST(d AS DATE) AS cal_date
    FROM generate_series(DATE '2025-11-01', DATE '2025-12-31', INTERVAL 1 DAY) AS t(d)
),
daily AS (
    SELECT order_date, COUNT(*) AS n
    FROM "warehouse"."legacy"."orders"
    WHERE order_date >= DATE '2025-11-01'
      AND order_date <= DATE '2025-12-31'
    GROUP BY order_date
)
SELECT
    c.cal_date,
    CAST(COALESCE(d.n, 0) AS INTEGER) AS orders_placed
FROM cal c
LEFT JOIN daily d
    ON d.order_date = c.cal_date
  );
