select cast(d.d as date) as cal_date, count(o.order_id) as orders_placed
from generate_series(date '2025-11-01', date '2025-12-31', interval 1 day) as d(d)
left join "warehouse"."legacy"."orders" o on o.order_date = cast(d.d as date)
group by 1