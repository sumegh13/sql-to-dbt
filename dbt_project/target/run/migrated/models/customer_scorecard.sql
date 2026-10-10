
  
  create view "warehouse"."main"."customer_scorecard__dbt_tmp" as (
    select c.customer_id,
  sum(case when lower(o.status) = 'shipped' then o.amount else 0 end) as shipped_amt,
  sum(case when lower(o.status) = 'pending' then o.amount else 0 end) as pending_amt,
  sum(case when lower(o.status) = 'cancelled' then o.amount else 0 end) as cancelled_amt,
  max(o.order_date) as last_order, count(o.order_id) as orders
from "warehouse"."legacy"."customers" c left join "warehouse"."legacy"."orders" o on o.customer_id = c.customer_id group by c.customer_id
  );
