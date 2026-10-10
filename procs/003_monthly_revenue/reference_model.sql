select year(order_date) as yr, month(order_date) as mo, sum(amount) as revenue
from {{ source('legacy', 'orders') }} where lower(status) not in ('cancelled','returned') group by 1, 2
