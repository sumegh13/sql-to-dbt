select employee_id, emp_name, department, salary,
  dense_rank() over (partition by department order by salary desc) as dept_rank,
  cast(salary * 100.0 / sum(salary) over (partition by department) as decimal(5,2)) as pct_of_dept
from {{ source('legacy', 'employees') }}
