
    

    create  table
      "warehouse"."main"."median_order_by_region__dbt_tmp"
  
    
    as (
      

SELECT
    MIN(c.region) AS region,
    quantile_cont(o.amount::DOUBLE, 0.5) AS median_amount
FROM "warehouse"."legacy"."orders" o
JOIN "warehouse"."legacy"."customers" c
    ON c.customer_id = o.customer_id
GROUP BY LOWER(RTRIM(c.region))
    );
    
  