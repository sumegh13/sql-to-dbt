CREATE OR ALTER PROCEDURE dbo.usp_hardware_not_software_buyers
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.hardware_not_software_buyers') IS NOT NULL DROP TABLE dbo.hardware_not_software_buyers;
SELECT DISTINCT o.customer_id INTO dbo.hardware_not_software_buyers FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id WHERE p.category = 'Hardware'
EXCEPT
SELECT DISTINCT o.customer_id FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id WHERE p.category = 'Software';
END
