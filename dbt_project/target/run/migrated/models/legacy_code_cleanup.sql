
  
  create view "warehouse"."main"."legacy_code_cleanup__dbt_tmp" as (
    WITH src AS (
    SELECT
        customer_id,
        legacy_code,
        TRIM(legacy_code) AS t
    FROM "warehouse"."legacy"."customers"
),
parsed AS (
    SELECT
        customer_id,
        legacy_code,
        CASE
            WHEN regexp_matches(t, '^[+-]?[0-9]+$') THEN TRY_CAST(t AS BIGINT)
        END AS n
    FROM src
)
SELECT
    customer_id,
    legacy_code,
    CASE
        WHEN n BETWEEN -2147483648 AND 2147483647 THEN CAST(n AS INTEGER)
    END AS legacy_code_num,
    CASE
        WHEN n IS NULL OR n NOT BETWEEN -2147483648 AND 2147483647 THEN 1
        ELSE 0
    END AS invalid
FROM parsed
  );
