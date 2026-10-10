
  
  create view "warehouse"."main"."running_total_cursor__dbt_tmp" as (
    select customer_id, order_id, order_date, amount,
  sum(amount) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and current row) as running_total
from "warehouse"."legacy"."orders"
  );
