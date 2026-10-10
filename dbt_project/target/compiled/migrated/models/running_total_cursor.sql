with ordered as (
    select
        customer_id,
        order_id,
        order_date,
        amount,
        sum(amount) over (
            partition by customer_id
            order by order_date asc nulls first, order_id asc nulls first
            rows between unbounded preceding and current row
        ) as running_sum,
        sum(case when amount is null then 1 else 0 end) over (
            partition by customer_id
            order by order_date asc nulls first, order_id asc nulls first
            rows between unbounded preceding and current row
        ) as null_amounts_seen
    from "warehouse"."legacy"."orders"
)
select
    customer_id,
    order_id,
    order_date,
    amount,
    cast(
        case
            when customer_id is null then amount
            when null_amounts_seen > 0 then null
            else running_sum
        end
        as decimal(18,2)
    ) as running_total
from ordered