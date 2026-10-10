select o.order_id, string_agg(p.product_name, ', ' order by p.product_name) as products
from {{ source('legacy', 'orders') }} o join {{ source('legacy', 'order_items') }} i on i.order_id = o.order_id
join {{ source('legacy', 'products') }} p on p.product_id = i.product_id group by o.order_id
