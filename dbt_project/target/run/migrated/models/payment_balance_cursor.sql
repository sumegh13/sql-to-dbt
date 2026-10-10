
  
  create view "warehouse"."main"."payment_balance_cursor__dbt_tmp" as (
    with src as (
    select
        p.payment_id,
        p.order_id,
        p.paid_amount,
        p.paid_date,
        o.amount
    from "warehouse"."legacy"."payments" p
    join "warehouse"."legacy"."orders" o
        on o.order_id = p.order_id
),
running as (
    select
        payment_id,
        order_id,
        paid_amount,
        amount,
        sum(paid_amount) over (
            partition by order_id
            order by paid_date nulls first, payment_id nulls first
            rows between unbounded preceding and current row
        ) as raw_running_sum,
        sum(case when paid_amount is null then 1 else 0 end) over (
            partition by order_id
            order by paid_date nulls first, payment_id nulls first
            rows between unbounded preceding and current row
        ) as null_paids_seen
    from src
),
final as (
    select
        payment_id,
        order_id,
        cast(paid_amount as decimal(18,2)) as paid_amount,
        case
            when null_paids_seen > 0 then cast(null as decimal(18,2))
            else cast(raw_running_sum as decimal(18,2))
        end as cumulative_paid,
        amount
    from running
)
select
    payment_id,
    order_id,
    paid_amount,
    cumulative_paid,
    cast(amount - cumulative_paid as decimal(18,2)) as balance_after,
    case when cumulative_paid > amount then 1 else 0 end as overpaid
from final
  );
