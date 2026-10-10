CREATE OR ALTER PROCEDURE dbo.usp_order_product_list
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.order_product_list') IS NOT NULL DROP TABLE dbo.order_product_list;
SELECT o.order_id, STRING_AGG(p.product_name, ', ') WITHIN GROUP (ORDER BY p.product_name) AS products
INTO dbo.order_product_list FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id
GROUP BY o.order_id;
END
