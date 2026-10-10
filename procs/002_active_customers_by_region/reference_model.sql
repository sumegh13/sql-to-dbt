select coalesce(region, 'Unknown') as region, count(*) as customer_count
from {{ source('legacy', 'customers') }} where is_active = 1 group by 1
