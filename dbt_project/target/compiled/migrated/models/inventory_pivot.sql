select product_id,
  coalesce(sum(qty_on_hand) filter (where warehouse = 'A'), 0) as wh_a,
  coalesce(sum(qty_on_hand) filter (where warehouse = 'B'), 0) as wh_b
from "warehouse"."legacy"."inventory" group by product_id