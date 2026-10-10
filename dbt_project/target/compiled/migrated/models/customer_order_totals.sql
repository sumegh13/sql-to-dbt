select c.customer_id, c.customer_name, count(o.order_id) as order_count,
       coalesce(sum(o.amount), 0) as total_amount,
       case when coalesce(sum(o.amount), 0) >= 1000 then 'gold'
            when coalesce(sum(o.amount), 0) >= 500 then 'silver' else 'bronze' end as tier
from "warehouse"."legacy"."customers" c
left join "warehouse"."legacy"."orders" o on o.customer_id = c.customer_id and lower(o.status) <> 'cancelled'
group by c.customer_id, c.customer_name