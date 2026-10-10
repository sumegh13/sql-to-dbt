select split_part(email, '@', 2) as domain, count(*) as customers
from {{ source('legacy', 'customers') }} where email is not null group by 1
