
  
  create view "warehouse"."main"."top_products_by_revenue__dbt_tmp" as (
    select p.product_id, p.product_name, sum(i.qty * i.unit_price) as revenue
from "warehouse"."legacy"."order_items" i join "warehouse"."legacy"."products" p on p.product_id = i.product_id
group by 1, 2 order by revenue desc, p.product_id limit 5
  );
