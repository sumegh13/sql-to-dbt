select customer_id, count(*) as total_orders,
  sum(case when lower(status) = 'cancelled' then 1 else 0 end) as cancelled_orders,
  sum(case when lower(status) = 'cancelled' then 1 else 0 end) * 100 // count(*) as cancel_pct
from {{ source('legacy', 'orders') }} group by customer_id
