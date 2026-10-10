
  
  create view "warehouse"."main"."merge_customer_dim__dbt_tmp" as (
    WITH target AS (
    SELECT customer_id, customer_name, region, email
    FROM "warehouse"."legacy"."customers"
),
staging AS (
    SELECT customer_id, customer_name, region, email
    FROM "warehouse"."legacy"."customer_staging"
),
matched AS (
    SELECT
        t.customer_id,
        s.customer_name,
        s.region,
        COALESCE(s.email, t.email) AS email
    FROM target t
    INNER JOIN staging s
        ON t.customer_id = s.customer_id
),
unmatched_target AS (
    SELECT t.customer_id, t.customer_name, t.region, t.email
    FROM target t
    WHERE NOT EXISTS (
        SELECT 1 FROM staging s WHERE s.customer_id = t.customer_id
    )
),
inserted AS (
    SELECT s.customer_id, s.customer_name, s.region, s.email
    FROM staging s
    WHERE NOT EXISTS (
        SELECT 1 FROM target t WHERE t.customer_id = s.customer_id
    )
)
SELECT customer_id, customer_name, region, email FROM matched
UNION ALL
SELECT customer_id, customer_name, region, email FROM unmatched_target
UNION ALL
SELECT customer_id, customer_name, region, email FROM inserted
  );
