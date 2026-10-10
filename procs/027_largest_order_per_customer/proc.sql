CREATE OR ALTER PROCEDURE dbo.usp_largest_order_per_customer
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.largest_order_per_customer') IS NOT NULL DROP TABLE dbo.largest_order_per_customer;
SELECT c.customer_id, t.order_id, t.amount INTO dbo.largest_order_per_customer FROM dbo.customers c
CROSS APPLY (SELECT TOP 1 o.order_id, o.amount FROM dbo.orders o WHERE o.customer_id = c.customer_id ORDER BY o.amount DESC, o.order_id) t;
END
