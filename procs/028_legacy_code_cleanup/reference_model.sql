select customer_id, legacy_code, try_cast(legacy_code as integer) as legacy_code_num,
  case when try_cast(legacy_code as integer) is null then 1 else 0 end as invalid
from {{ source('legacy', 'customers') }}
