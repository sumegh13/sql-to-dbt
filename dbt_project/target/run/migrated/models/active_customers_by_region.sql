
  
  create view "warehouse"."main"."active_customers_by_region__dbt_tmp" as (
    select coalesce(region, 'Unknown') as region, count(*) as customer_count
from "warehouse"."legacy"."customers" where is_active = 1 group by 1
  );
