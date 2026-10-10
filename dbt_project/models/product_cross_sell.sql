select
    a.product_id as product_a,
    b.product_id as product_b,
    count(distinct a.order_id) as together
from {{ source('legacy', 'order_items') }} a
join {{ source('legacy', 'order_items') }} b
    on a.order_id = b.order_id
    and a.product_id < b.product_id
group by a.product_id, b.product_id