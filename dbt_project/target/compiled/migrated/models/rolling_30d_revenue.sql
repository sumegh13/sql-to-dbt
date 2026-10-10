select d.order_date, sum(o2.amount) as rolling_30d
from (select distinct order_date from "warehouse"."legacy"."orders") d
left join "warehouse"."legacy"."orders" o2 on o2.order_date > d.order_date - 30 and o2.order_date <= d.order_date
  and lower(o2.status) not in ('cancelled','returned')
group by d.order_date