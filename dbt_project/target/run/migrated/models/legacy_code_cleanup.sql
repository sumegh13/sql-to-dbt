
  
  create view "warehouse"."main"."legacy_code_cleanup__dbt_tmp" as (
    select customer_id, legacy_code, try_cast(legacy_code as integer) as legacy_code_num,
  case when try_cast(legacy_code as integer) is null then 1 else 0 end as invalid
from "warehouse"."legacy"."customers"
  );
