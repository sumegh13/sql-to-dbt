
  
  create view "warehouse"."main"."legacy_code_cleanup__dbt_tmp" as (
    WITH src AS (
    SELECT
        customer_id,
        legacy_code,
        trim(legacy_code, ' ') AS code_trimmed
    FROM "warehouse"."legacy"."customers"
),
parsed AS (
    SELECT
        customer_id,
        legacy_code,
        code_trimmed,
        CASE
            WHEN code_trimmed = '' THEN 0
            WHEN regexp_matches(code_trimmed, '^[+-]?[0-9]+$') THEN TRY_CAST(code_trimmed AS INTEGER)
            ELSE NULL
        END AS legacy_code_num
    FROM src
)
SELECT
    customer_id,
    legacy_code,
    legacy_code_num,
    CASE WHEN legacy_code_num IS NULL THEN 1 ELSE 0 END AS invalid
FROM parsed
  );
