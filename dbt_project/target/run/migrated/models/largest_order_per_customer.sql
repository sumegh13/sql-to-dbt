
  
  create view "warehouse"."main"."largest_order_per_customer__dbt_tmp" as (
    select customer_id, order_id, amount from "warehouse"."legacy"."orders"
qualify row_number() over (partition by customer_id order by amount desc, order_id) = 1
  );
