
  
  create view "warehouse"."main"."customer_scorecard__dbt_tmp" as (
    SELECT
    c.customer_id,
    SUM(CASE WHEN rtrim(lower(o.status)) = 'shipped' THEN o.amount ELSE CAST(0 AS DECIMAL(18,2)) END) AS shipped_amt,
    SUM(CASE WHEN rtrim(lower(o.status)) = 'pending' THEN o.amount ELSE CAST(0 AS DECIMAL(18,2)) END) AS pending_amt,
    SUM(CASE WHEN rtrim(lower(o.status)) = 'cancelled' THEN o.amount ELSE CAST(0 AS DECIMAL(18,2)) END) AS cancelled_amt,
    MAX(o.order_date) AS last_order,
    COUNT(o.order_id) AS orders
FROM "warehouse"."legacy"."customers" c
LEFT JOIN "warehouse"."legacy"."orders" o
    ON o.customer_id = c.customer_id
GROUP BY c.customer_id
  );
