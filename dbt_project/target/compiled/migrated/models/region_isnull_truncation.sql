SELECT
    customer_id,
    CASE WHEN region IS NULL THEN LEFT('Not_Assigned_Yet', 10) ELSE region END AS region_isnull,
    COALESCE(region, 'Not_Assigned_Yet') AS region_coalesce
FROM "warehouse"."legacy"."customers"