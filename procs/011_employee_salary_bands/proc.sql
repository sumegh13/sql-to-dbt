CREATE OR ALTER PROCEDURE dbo.usp_employee_salary_bands
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.employee_salary_bands') IS NOT NULL DROP TABLE dbo.employee_salary_bands;
SELECT employee_id, emp_name, salary, IIF(salary >= 120000, 'senior', IIF(salary >= 70000, 'mid', 'junior')) AS band
INTO dbo.employee_salary_bands FROM dbo.employees;
END
