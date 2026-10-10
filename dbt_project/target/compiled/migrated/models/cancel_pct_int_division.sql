select
    customer_id,
    cast(count(*) as integer) as total_orders,
    cast(sum(case when upper(rtrim(status)) = 'CANCELLED' then 1 else 0 end) as integer) as cancelled_orders,
    cast(
        (sum(case when upper(rtrim(status)) = 'CANCELLED' then 1 else 0 end) * 100) // count(*)
        as integer
    ) as cancel_pct
from "warehouse"."legacy"."orders"
group by customer_id