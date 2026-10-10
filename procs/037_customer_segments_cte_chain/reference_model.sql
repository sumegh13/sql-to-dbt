with a as (select order_id, customer_id, amount from {{ source('legacy', 'orders') }} where lower(status) not in ('cancelled','returned')),
b as (select customer_id, count(*) as n, sum(amount) as s from a group by customer_id),
c as (select customer_id, n, s, s / n as avg_amt from b),
d as (select customer_id, n, s, avg_amt, case when n >= 3 then 'frequent' when n = 2 then 'repeat' else 'one_off' end as segment from c)
select * from d
