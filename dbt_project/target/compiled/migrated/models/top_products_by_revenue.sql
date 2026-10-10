with revenue_by_product as (
    select
        p.product_id,
        p.product_name,
        cast(sum(cast(i.qty * i.unit_price as decimal(38,2))) as decimal(38,2)) as revenue
    from "warehouse"."legacy"."order_items" i
    join "warehouse"."legacy"."products" p
        on p.product_id = i.product_id
    group by p.product_id, p.product_name
)
select
    product_id,
    product_name,
    revenue
from revenue_by_product
order by revenue desc nulls last, product_id
limit 5