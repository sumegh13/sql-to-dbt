
  
  create view "warehouse"."main"."east_markup_update_delete__dbt_tmp" as (
    select o.order_id, o.customer_id,
  case when c.region = 'East' then round(o.amount * 1.1, 2) else o.amount end as amount, o.status
from "warehouse"."legacy"."orders" o left join "warehouse"."legacy"."customers" c on c.customer_id = o.customer_id
where lower(o.status) <> 'cancelled'
  );
