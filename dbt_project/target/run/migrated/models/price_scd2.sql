
  
  create view "warehouse"."main"."price_scd2__dbt_tmp" as (
    select product_id, price, effective_date as valid_from,
  coalesce(lead(effective_date) over (partition by product_id order by effective_date), date '9999-12-31') as valid_to,
  case when lead(effective_date) over (partition by product_id order by effective_date) is null then 1 else 0 end as is_current
from "warehouse"."legacy"."price_history"
  );
