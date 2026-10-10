
  
  create view "warehouse"."main"."order_rank_per_customer__dbt_tmp" as (
    select order_id, customer_id, amount,
  row_number() over (partition by customer_id order by amount desc, order_id) as rn,
  rank() over (partition by customer_id order by amount desc) as rnk,
  dense_rank() over (partition by customer_id order by amount desc) as drnk
from "warehouse"."legacy"."orders"
  );
