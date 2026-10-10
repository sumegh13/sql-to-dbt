select c.region, count(distinct c.customer_id) as buyers
from {{ source('legacy', 'customers') }} c join {{ source('legacy', 'orders') }} o on o.customer_id = c.customer_id group by c.region
