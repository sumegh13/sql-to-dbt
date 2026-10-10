CREATE OR ALTER PROCEDURE dbo.usp_buyers_by_region
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.buyers_by_region') IS NOT NULL DROP TABLE dbo.buyers_by_region;
SELECT c.region, COUNT(DISTINCT c.customer_id) AS buyers INTO dbo.buyers_by_region
FROM dbo.customers c JOIN dbo.orders o ON o.customer_id = c.customer_id GROUP BY c.region;
END
