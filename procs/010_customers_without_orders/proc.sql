CREATE OR ALTER PROCEDURE dbo.usp_customers_without_orders
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customers_without_orders') IS NOT NULL DROP TABLE dbo.customers_without_orders;
SELECT c.customer_id, c.customer_name INTO dbo.customers_without_orders FROM dbo.customers c
WHERE NOT EXISTS (SELECT 1 FROM dbo.orders o WHERE o.customer_id = c.customer_id);
END
