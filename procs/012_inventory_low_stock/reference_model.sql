select p.product_id, p.product_name, sum(inv.qty_on_hand) as total_qty,
  case when sum(inv.qty_on_hand) < 20 then 1 else 0 end as low_stock
from {{ source('legacy', 'products') }} p left join {{ source('legacy', 'inventory') }} inv on inv.product_id = p.product_id
group by 1, 2
