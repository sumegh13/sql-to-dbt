
  
  create view "warehouse"."main"."avg_item_by_category__dbt_tmp" as (
    select p.category, avg(i.qty * i.unit_price) as avg_line_value, count(*) as line_count
from "warehouse"."legacy"."order_items" i join "warehouse"."legacy"."products" p on p.product_id = i.product_id group by 1
  );
