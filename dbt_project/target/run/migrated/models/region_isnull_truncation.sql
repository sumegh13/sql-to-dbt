
  
  create view "warehouse"."main"."region_isnull_truncation__dbt_tmp" as (
    select customer_id,
  coalesce(region, left('Not_Assigned_Yet', 10)) as region_isnull,
  coalesce(region, 'Not_Assigned_Yet') as region_coalesce
from "warehouse"."legacy"."customers"
  );
