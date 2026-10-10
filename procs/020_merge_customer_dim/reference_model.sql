select coalesce(s.customer_id, t.customer_id) as customer_id,
  case when s.customer_id is not null then s.customer_name else t.customer_name end as customer_name,
  case when s.customer_id is not null then s.region else t.region end as region,
  coalesce(s.email, t.email) as email
from {{ source('legacy', 'customers') }} t full outer join {{ source('legacy', 'customer_staging') }} s on t.customer_id = s.customer_id
