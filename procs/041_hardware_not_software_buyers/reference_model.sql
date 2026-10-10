select distinct o.customer_id from {{ source('legacy', 'orders') }} o
join {{ source('legacy', 'order_items') }} i on i.order_id = o.order_id join {{ source('legacy', 'products') }} p on p.product_id = i.product_id where p.category = 'Hardware'
except
select distinct o.customer_id from {{ source('legacy', 'orders') }} o
join {{ source('legacy', 'order_items') }} i on i.order_id = o.order_id join {{ source('legacy', 'products') }} p on p.product_id = i.product_id where p.category = 'Software'
