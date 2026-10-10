select distinct o.customer_id from "warehouse"."legacy"."orders" o
join "warehouse"."legacy"."order_items" i on i.order_id = o.order_id join "warehouse"."legacy"."products" p on p.product_id = i.product_id where p.category = 'Hardware'
except
select distinct o.customer_id from "warehouse"."legacy"."orders" o
join "warehouse"."legacy"."order_items" i on i.order_id = o.order_id join "warehouse"."legacy"."products" p on p.product_id = i.product_id where p.category = 'Software'