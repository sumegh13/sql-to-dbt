
  
  create view "warehouse"."main"."org_hierarchy__dbt_tmp" as (
    with recursive h as (
  select
    employee_id,
    emp_name,
    manager_id,
    0 as lvl,
    cast(emp_name as varchar) as path
  from "warehouse"."legacy"."employees"
  where manager_id is null

  union all

  select
    e.employee_id,
    e.emp_name,
    e.manager_id,
    h.lvl + 1 as lvl,
    left(h.path || ' > ' || e.emp_name, 500) as path
  from "warehouse"."legacy"."employees" e
  join h on e.manager_id = h.employee_id
)
select
  employee_id,
  emp_name,
  lvl,
  path
from h
  );
