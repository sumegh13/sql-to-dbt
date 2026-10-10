
  
  create view "warehouse"."main"."customer_spend_quartiles__dbt_tmp" as (
    with s as (select customer_id, sum(amount) as spend from "warehouse"."legacy"."orders"
           where lower(status) not in ('cancelled','returned') group by customer_id)
select customer_id, spend, ntile(4) over (order by spend desc, customer_id) as quartile from s
  );
