select
    o.order_id,
    o.amount,
    coalesce(sum(p.paid_amount), 0) as paid,
    case
        when coalesce(sum(p.paid_amount), 0) >= o.amount then 'paid'
        when coalesce(sum(p.paid_amount), 0) > 0 then 'partial'
        else 'unpaid'
    end as payment_status
from "warehouse"."legacy"."orders" o
left join "warehouse"."legacy"."payments" p
    on p.order_id = o.order_id
group by o.order_id, o.amount