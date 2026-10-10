with order_totals as (
    select
        customer_id,
        count(*) as order_count,
        sum(amount) as total_amount
    from "warehouse"."legacy"."orders"
    where customer_id is not null
      and status is not null
      and lower(rtrim(status)) <> 'cancelled'
    group by customer_id
),
calc as (
    select
        c.customer_id,
        c.customer_name,
        cast(coalesce(ot.order_count, 0) as integer) as order_count,
        cast(coalesce(ot.total_amount, 0) as decimal(18,2)) as total_amount
    from "warehouse"."legacy"."customers" c
    left join order_totals ot
        on ot.customer_id = c.customer_id
)
select
    customer_id,
    customer_name,
    order_count,
    total_amount,
    case
        when total_amount >= 1000 then 'gold'
        when total_amount >= 500 then 'silver'
        else 'bronze'
    end as tier
from calc