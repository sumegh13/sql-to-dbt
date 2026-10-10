with m as (select year(order_date) as yr, month(order_date) as mo, sum(amount) as rev from "warehouse"."legacy"."orders"
           where lower(status) not in ('cancelled','returned') group by 1, 2)
select yr, mo, rev, lag(rev) over (order by yr, mo) as prev_rev,
  round((rev - lag(rev) over (order by yr, mo)) * 100.0 / nullif(lag(rev) over (order by yr, mo), 0), 2) as growth_pct
from m