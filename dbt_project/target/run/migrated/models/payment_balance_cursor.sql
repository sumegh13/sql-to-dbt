
  
  create view "warehouse"."main"."payment_balance_cursor__dbt_tmp" as (
    with joined as (
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
        -- T-SQL cursor: once a NULL payment enters the running total, it stays NULL for the rest of the order
        case
            when count(*) over (
                    partition by order_id
                    order by paid_date nulls first, payment_id
                    rows between unbounded preceding and current row)
                 = count(paid_amount) over (
                    partition by order_id
                    order by paid_date nulls first, payment_id
                    rows between unbounded preceding and current row)
            then cast(sum(paid_amount) over (
                    partition by order_id
                    order by paid_date nulls first, payment_id
                    rows between unbounded preceding and current row) as decimal(18,2))
            else cast(null as decimal(18,2))
        end as cumulative_paid
    from joined
)
select
    payment_id,
    order_id,
    cast(paid_amount as decimal(18,2)) as paid_amount,
    cumulative_paid,
    cast(amount - cumulative_paid as decimal(18,2)) as balance_after,
    cast(case when cumulative_paid > amount then 1 else 0 end as integer) as overpaid
from running
  );
