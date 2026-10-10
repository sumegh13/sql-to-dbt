CREATE OR ALTER PROCEDURE dbo.usp_org_hierarchy
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.org_hierarchy') IS NOT NULL DROP TABLE dbo.org_hierarchy;
WITH h AS (
  SELECT employee_id, emp_name, manager_id, 0 AS lvl, CAST(emp_name AS VARCHAR(500)) AS path
  FROM dbo.employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.employee_id, e.emp_name, e.manager_id, h.lvl + 1, CAST(h.path + ' > ' + e.emp_name AS VARCHAR(500))
  FROM dbo.employees e JOIN h ON e.manager_id = h.employee_id)
SELECT employee_id, emp_name, lvl, path INTO dbo.org_hierarchy FROM h;
END
