
  
  create view "warehouse"."main"."product_cross_sell__dbt_tmp" as (
    select a.product_id as product_a, b.product_id as product_b, count(distinct a.order_id) as together
from "warehouse"."legacy"."order_items" a join "warehouse"."legacy"."order_items" b on a.order_id = b.order_id and a.product_id < b.product_id
group by 1, 2
  );
