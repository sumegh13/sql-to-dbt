CREATE OR ALTER PROCEDURE dbo.usp_dept_salary_rank
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.dept_salary_rank') IS NOT NULL DROP TABLE dbo.dept_salary_rank;
SELECT employee_id, emp_name, department, salary,
  DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank,
  CAST(salary * 100.0 / SUM(salary) OVER (PARTITION BY department) AS DECIMAL(5,2)) AS pct_of_dept
INTO dbo.dept_salary_rank FROM dbo.employees;
END
