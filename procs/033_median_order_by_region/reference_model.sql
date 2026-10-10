select c.region, quantile_cont(cast(o.amount as double), 0.5) as median_amount
from {{ source('legacy', 'orders') }} o join {{ source('legacy', 'customers') }} c on c.customer_id = o.customer_id group by c.region
