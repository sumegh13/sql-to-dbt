select order_id, customer_id, order_date,
  lag(order_date) over (partition by customer_id order by order_date, order_id) as prev_date,
  case when date_diff('day', lag(order_date) over (partition by customer_id order by order_date, order_id), order_date) <= 7 then 1 else 0 end as is_repeat_7d
from "warehouse"."legacy"."orders"