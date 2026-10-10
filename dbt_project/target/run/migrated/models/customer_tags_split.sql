
  
  create view "warehouse"."main"."customer_tags_split__dbt_tmp" as (
    WITH split_tags AS (
    SELECT
        c.customer_id,
        unnest(
            CASE
                WHEN c.tags = '' THEN ['']
                ELSE string_split(c.tags, ',')
            END
        ) AS raw_tag
    FROM "warehouse"."legacy"."customers" c
    WHERE c.tags IS NOT NULL
)
SELECT
    customer_id,
    LTRIM(RTRIM(raw_tag)) AS tag
FROM split_tags
  );
