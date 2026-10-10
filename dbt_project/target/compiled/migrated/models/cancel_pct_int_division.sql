with base as (
    select
        customer_id,
        case when rtrim(lower(status)) = 'cancelled' then 1 else 0 end as is_cancelled
    from "warehouse"."legacy"."orders"
)
select
    customer_id,
    count(*) as total_orders,
    cast(sum(is_cancelled) as integer) as cancelled_orders,
    cast(sum(is_cancelled) * 100 // count(*) as integer) as cancel_pct
from base
group by customer_id