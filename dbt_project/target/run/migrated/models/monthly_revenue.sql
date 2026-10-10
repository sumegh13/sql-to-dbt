
  
  create view "warehouse"."main"."monthly_revenue__dbt_tmp" as (
    SELECT
    CAST(YEAR(order_date) AS INTEGER) AS yr,
    CAST(MONTH(order_date) AS INTEGER) AS mo,
    CAST(SUM(amount) AS DECIMAL(38,2)) AS revenue
FROM "warehouse"."legacy"."orders"
WHERE UPPER(RTRIM(status)) NOT IN ('CANCELLED', 'RETURNED')
GROUP BY YEAR(order_date), MONTH(order_date)
  );
