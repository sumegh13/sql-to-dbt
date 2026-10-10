CREATE OR ALTER PROCEDURE dbo.usp_median_order_by_region
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.median_order_by_region') IS NOT NULL DROP TABLE dbo.median_order_by_region;
SELECT DISTINCT c.region, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.amount) OVER (PARTITION BY c.region) AS median_amount
INTO dbo.median_order_by_region FROM dbo.orders o JOIN dbo.customers c ON c.customer_id = o.customer_id;
END
