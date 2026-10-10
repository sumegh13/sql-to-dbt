WITH tgt AS (
    SELECT customer_id, customer_name, region, email
    FROM "warehouse"."legacy"."customers"
),
stg AS (
    SELECT customer_id, customer_name, region, email
    FROM "warehouse"."legacy"."customer_staging"
),
matched AS (
    -- WHEN MATCHED: name and region come from staging; email falls back to target when staging email is NULL
    SELECT t.customer_id,
           s.customer_name,
           s.region,
           COALESCE(s.email, t.email) AS email
    FROM tgt t
    INNER JOIN stg s ON t.customer_id = s.customer_id
),
kept AS (
    -- Target rows with no matching staging row are unchanged
    SELECT t.customer_id, t.customer_name, t.region, t.email
    FROM tgt t
    WHERE NOT EXISTS (
        SELECT 1 FROM stg s WHERE s.customer_id = t.customer_id
    )
),
inserted AS (
    -- WHEN NOT MATCHED BY TARGET: staging rows with no matching target row are inserted
    SELECT s.customer_id, s.customer_name, s.region, s.email
    FROM stg s
    WHERE NOT EXISTS (
        SELECT 1 FROM tgt t WHERE t.customer_id = s.customer_id
    )
)
SELECT customer_id, customer_name, region, email FROM matched
UNION ALL
SELECT customer_id, customer_name, region, email FROM kept
UNION ALL
SELECT customer_id, customer_name, region, email FROM inserted