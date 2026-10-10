CREATE OR ALTER PROCEDURE dbo.usp_region_isnull_truncation
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.region_isnull_truncation') IS NOT NULL DROP TABLE dbo.region_isnull_truncation;
SELECT customer_id, ISNULL(region, 'Not_Assigned_Yet') AS region_isnull, COALESCE(region, 'Not_Assigned_Yet') AS region_coalesce
INTO dbo.region_isnull_truncation FROM dbo.customers;
END
