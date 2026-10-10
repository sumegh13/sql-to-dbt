select split_part(email, '@', 2) as domain, count(*) as customers
from "warehouse"."legacy"."customers" where email is not null group by 1