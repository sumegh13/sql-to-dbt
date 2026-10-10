CREATE OR ALTER PROCEDURE dbo.usp_active_customers_by_region
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.active_customers_by_region') IS NOT NULL DROP TABLE dbo.active_customers_by_region;
SELECT ISNULL(region,'Unknown') AS region, COUNT(*) AS customer_count INTO dbo.active_customers_by_region
FROM dbo.customers WHERE is_active = 1 GROUP BY ISNULL(region,'Unknown');
END
