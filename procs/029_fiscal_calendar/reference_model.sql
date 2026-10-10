select order_id, order_date, last_day(order_date) as month_end,
  case when month(order_date) >= 4 then year(order_date) + 1 else year(order_date) end as fiscal_year,
  ((month(order_date) + 8) % 12) // 3 + 1 as fiscal_qtr,
  dayname(order_date) as dow
from {{ source('legacy', 'orders') }}
