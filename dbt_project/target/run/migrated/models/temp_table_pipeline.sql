
  
  create view "warehouse"."main"."temp_table_pipeline__dbt_tmp" as (
    with spend as (
  select customer_id, sum(amount) as spend from "warehouse"."legacy"."orders"
  where lower(status) not in ('cancelled','returned') group by customer_id),
joined as (
  select c.customer_id, c.customer_name, coalesce(s.spend, 0) as spend
  from "warehouse"."legacy"."customers" c left join spend s on s.customer_id = c.customer_id)
select j.customer_id, j.customer_name, j.spend,
  case when j.spend > (select avg(spend) from joined) then 'above_avg' else 'at_or_below_avg' end as vs_avg
from joined j
  );
