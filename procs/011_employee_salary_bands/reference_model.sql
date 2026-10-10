select employee_id, emp_name, salary,
  case when salary >= 120000 then 'senior' when salary >= 70000 then 'mid' else 'junior' end as band
from {{ source('legacy', 'employees') }}
