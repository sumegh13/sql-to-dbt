SELECT
  order_id,
  order_date,
  last_day(order_date) AS month_end,
  CASE WHEN month(order_date) >= 4 THEN year(order_date) + 1 ELSE year(order_date) END AS fiscal_year,
  ((month(order_date) + 8) % 12) // 3 + 1 AS fiscal_qtr,
  strftime(order_date, '%A') AS dow
FROM "warehouse"."legacy"."orders"