select p.payment_id, p.order_id, p.paid_amount,
  sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) as cumulative_paid,
  o.amount - sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) as balance_after,
  case when sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) > o.amount then 1 else 0 end as overpaid
from "warehouse"."legacy"."payments" p join "warehouse"."legacy"."orders" o on o.order_id = p.order_id