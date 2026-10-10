
  
  create view "warehouse"."main"."dept_salary_rank__dbt_tmp" as (
    WITH base AS (
    SELECT
        employee_id,
        emp_name,
        department,
        salary,
        RTRIM(LOWER(department)) AS dept_key,
        CAST(salary * 100 AS BIGINT) AS salary_cents
    FROM "warehouse"."legacy"."employees"
),
calc AS (
    SELECT
        *,
        SUM(salary_cents) OVER (PARTITION BY dept_key) AS dept_cents
    FROM base
)
SELECT
    employee_id,
    emp_name,
    department,
    salary,
    DENSE_RANK() OVER (PARTITION BY dept_key ORDER BY salary DESC) AS dept_rank,
    CAST(((2 * salary_cents * 10000) + dept_cents) // (2 * dept_cents) / 100.0 AS DECIMAL(5,2)) AS pct_of_dept
FROM calc
  );
