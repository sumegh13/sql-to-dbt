select customer_id,
  count(*) filter (where lower(status) = 'shipped') as shipped,
  count(*) filter (where lower(status) = 'pending') as pending,
  count(*) filter (where lower(status) = 'cancelled') as cancelled
from "warehouse"."legacy"."orders" group by customer_id