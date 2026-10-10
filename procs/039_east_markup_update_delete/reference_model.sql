select o.order_id, o.customer_id,
  case when c.region = 'East' then round(o.amount * 1.1, 2) else o.amount end as amount, o.status
from {{ source('legacy', 'orders') }} o left join {{ source('legacy', 'customers') }} c on c.customer_id = o.customer_id
where lower(o.status) <> 'cancelled'
