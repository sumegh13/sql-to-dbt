select order_id, date_diff('day', order_date, date '2025-12-31') as age_days,
  case when date_diff('day', order_date, date '2025-12-31') <= 30 then '0-30'
       when date_diff('day', order_date, date '2025-12-31') <= 90 then '31-90' else '90+' end as bucket
from "warehouse"."legacy"."orders"