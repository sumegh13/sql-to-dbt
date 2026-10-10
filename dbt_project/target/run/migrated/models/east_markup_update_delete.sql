
  
  create view "warehouse"."main"."east_markup_update_delete__dbt_tmp" as (
    WITH east_customers AS (
    SELECT DISTINCT customer_id
    FROM "warehouse"."legacy"."customers"
    WHERE lower(rtrim(region)) = 'east'
      AND customer_id IS NOT NULL
)
SELECT
    o.order_id,
    o.customer_id,
    CASE
        WHEN ec.customer_id IS NOT NULL
            THEN CAST(o.amount * 1.1 AS DECIMAL(18,2))
        ELSE o.amount
    END AS amount,
    o.status
FROM "warehouse"."legacy"."orders" o
LEFT JOIN east_customers ec
    ON ec.customer_id = o.customer_id
WHERE o.status IS NULL
   OR lower(rtrim(o.status)) <> 'cancelled'
  );
