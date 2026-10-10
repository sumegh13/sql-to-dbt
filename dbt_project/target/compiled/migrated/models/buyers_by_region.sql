select c.region, count(distinct c.customer_id) as buyers
from "warehouse"."legacy"."customers" c join "warehouse"."legacy"."orders" o on o.customer_id = c.customer_id group by c.region