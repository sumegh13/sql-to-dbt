
  
  create view "warehouse"."main"."customer_spend_quartiles__dbt_tmp" as (
    WITH s AS (
    SELECT
        customer_id,
        SUM(amount) AS spend
    FROM "warehouse"."legacy"."orders"
    WHERE rtrim(lower(status)) NOT IN ('cancelled', 'returned')
    GROUP BY customer_id
)
SELECT
    customer_id,
    spend,
    NTILE(4) OVER (ORDER BY spend DESC NULLS LAST, customer_id ASC NULLS FIRST) AS quartile
FROM s
  );
