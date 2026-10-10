SELECT
    employee_id,
    emp_name,
    salary,
    CASE
        WHEN salary >= 120000 THEN 'senior'
        WHEN salary >= 70000 THEN 'mid'
        ELSE 'junior'
    END AS band
FROM "warehouse"."legacy"."employees"