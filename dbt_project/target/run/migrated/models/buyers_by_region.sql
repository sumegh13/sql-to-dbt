
  
  create view "warehouse"."main"."buyers_by_region__dbt_tmp" as (
    SELECT
    MIN(c.region) AS region,
    COUNT(DISTINCT c.customer_id) AS buyers
FROM "warehouse"."legacy"."customers" c
JOIN "warehouse"."legacy"."orders" o
    ON o.customer_id = c.customer_id
GROUP BY UPPER(RTRIM(c.region))
  );
