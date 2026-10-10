select c.customer_id, c.customer_name from {{ source('legacy', 'customers') }} c
where not exists (select 1 from {{ source('legacy', 'orders') }} o where o.customer_id = c.customer_id)
