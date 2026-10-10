select item_id, order_id, qty, running_qty,
  case when running_qty >= 10 then 10 when running_qty >= 5 then 5 else 0 end as discount_pct
from (select item_id, order_id, qty,
        cast(sum(qty) over (partition by order_id order by item_id rows between unbounded preceding and current row) as integer) as running_qty
      from "warehouse"."legacy"."order_items") t