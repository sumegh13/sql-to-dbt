select distinct customer_id,
  first_value(order_id) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and unbounded following) as first_order,
  last_value(order_id) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and unbounded following) as last_order
from "warehouse"."legacy"."orders"