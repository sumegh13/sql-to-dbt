
  
  create view "warehouse"."main"."region_isnull_truncation__dbt_tmp" as (
    SELECT
    customer_id,
    COALESCE(region, LEFT('Not_Assigned_Yet', 10)) AS region_isnull,
    COALESCE(region, 'Not_Assigned_Yet') AS region_coalesce
FROM "warehouse"."legacy"."customers"
  );
