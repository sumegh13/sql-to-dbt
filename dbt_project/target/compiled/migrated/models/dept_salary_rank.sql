WITH base AS (
    SELECT
        employee_id,
        emp_name,
        department,
        salary,
        RTRIM(LOWER(department)) AS dept_key,
        CAST(salary * 100 AS BIGINT) AS sal_c
    FROM "warehouse"."legacy"."employees"
),
ranked AS (
    SELECT
        employee_id,
        emp_name,
        department,
        salary,
        sal_c,
        DENSE_RANK() OVER (PARTITION BY dept_key ORDER BY salary DESC) AS dept_rank,
        SUM(sal_c) OVER (PARTITION BY dept_key) AS tot_c
    FROM base
),
calc AS (
    SELECT
        employee_id,
        emp_name,
        department,
        salary,
        dept_rank,
        CASE
            WHEN tot_c = 0 THEN NULL
            ELSE (CASE WHEN (sal_c < 0) <> (tot_c < 0) THEN -1 ELSE 1 END)
                 * ((20000 * ABS(sal_c) + ABS(tot_c)) // (2 * ABS(tot_c)))
        END AS hund
    FROM ranked
)
SELECT
    employee_id,
    emp_name,
    department,
    salary,
    dept_rank,
    CAST(CAST(hund AS DECIMAL(18, 0)) * CAST(0.01 AS DECIMAL(3, 2)) AS DECIMAL(5, 2)) AS pct_of_dept
FROM calc