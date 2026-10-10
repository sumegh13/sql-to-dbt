
  
  create view "warehouse"."main"."customer_name_cleanup__dbt_tmp" as (
    select customer_id, upper(trim(customer_name)) as clean_name, left(ltrim(customer_name), 1) as initial,
  customer_name || ' <' || email || '>' as display,
  replace(lower(trim(customer_name)), ' ', '_') as slug, length(rtrim(customer_name)) as name_len
from "warehouse"."legacy"."customers"
  );
