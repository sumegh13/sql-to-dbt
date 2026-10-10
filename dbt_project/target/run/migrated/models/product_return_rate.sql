
  
  create view "warehouse"."main"."product_return_rate__dbt_tmp" as (
    select p.product_id, p.product_name, count(*) as line_count,
  sum(case when lower(o.status) = 'returned' then 1 else 0 end) as returned_lines,
  cast(sum(case when lower(o.status) = 'returned' then 1 else 0 end) as double) / count(*) as return_rate
from "warehouse"."legacy"."order_items" i join "warehouse"."legacy"."orders" o on o.order_id = i.order_id
join "warehouse"."legacy"."products" p on p.product_id = i.product_id group by 1, 2
  );
