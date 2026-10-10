
  
  create view "warehouse"."main"."customer_name_cleanup__dbt_tmp" as (
    SELECT
    customer_id,
    UPPER(LTRIM(RTRIM(customer_name))) AS clean_name,
    LEFT(LTRIM(customer_name), 1) AS initial,
    customer_name || ' <' || email || '>' AS display,
    REPLACE(LOWER(LTRIM(RTRIM(customer_name))), ' ', '_') AS slug,
    CAST(LENGTH(RTRIM(customer_name)) AS INTEGER) AS name_len
FROM "warehouse"."legacy"."customers"
  );
