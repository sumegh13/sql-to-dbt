
  
  create view "warehouse"."main"."order_streaks__dbt_tmp" as (
    with d as (select distinct customer_id, order_date from "warehouse"."legacy"."orders"),
g as (select customer_id, order_date,
        order_date - cast(row_number() over (partition by customer_id order by order_date) as integer) as grp from d)
select customer_id, min(order_date) as streak_start, max(order_date) as streak_end, count(*) as days
from g group by customer_id, grp
  );
