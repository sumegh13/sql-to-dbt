select o.order_id, o.amount, coalesce(x.total, 0) as paid, o.amount - coalesce(x.total, 0) as outstanding, x.last_dt as last_paid
from {{ source('legacy', 'orders') }} o
left join (select order_id, sum(paid_amount) as total, max(paid_date) as last_dt from {{ source('legacy', 'payments') }} group by order_id) x
  on x.order_id = o.order_id
