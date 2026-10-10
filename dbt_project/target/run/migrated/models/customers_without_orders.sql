
  
  create view "warehouse"."main"."customers_without_orders__dbt_tmp" as (
    select c.customer_id, c.customer_name from "warehouse"."legacy"."customers" c
where not exists (select 1 from "warehouse"."legacy"."orders" o where o.customer_id = c.customer_id)
  );
