
  
  create view "warehouse"."main"."fiscal_calendar__dbt_tmp" as (
    SELECT
  order_id,
  order_date,
  last_day(order_date) AS month_end,
  CAST(CASE WHEN EXTRACT(MONTH FROM order_date) >= 4
            THEN EXTRACT(YEAR FROM order_date) + 1
            ELSE EXTRACT(YEAR FROM order_date) END AS INTEGER) AS fiscal_year,
  CAST(((EXTRACT(MONTH FROM order_date) + 8) % 12) // 3 + 1 AS INTEGER) AS fiscal_qtr,
  strftime(order_date, '%A') AS dow
FROM "warehouse"."legacy"."orders"
  );
