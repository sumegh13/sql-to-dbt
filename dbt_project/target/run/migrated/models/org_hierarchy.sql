
  
  create view "warehouse"."main"."org_hierarchy__dbt_tmp" as (
    WITH RECURSIVE h AS (
  SELECT employee_id, emp_name, manager_id, 0 AS lvl, CAST(emp_name AS VARCHAR) AS path
  FROM "warehouse"."legacy"."employees"
  WHERE manager_id IS NULL
  UNION ALL
  SELECT e.employee_id, e.emp_name, e.manager_id, h.lvl + 1,
         LEFT(h.path || ' > ' || e.emp_name, 500)
  FROM "warehouse"."legacy"."employees" e
  JOIN h ON e.manager_id = h.employee_id
)
SELECT employee_id, emp_name, lvl, path
FROM h
  );
