CREATE OR ALTER PROCEDURE dbo.usp_top_products_by_revenue
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.top_products_by_revenue') IS NOT NULL DROP TABLE dbo.top_products_by_revenue;
SELECT TOP 5 p.product_id, p.product_name, SUM(i.qty * i.unit_price) AS revenue INTO dbo.top_products_by_revenue
FROM dbo.order_items i JOIN dbo.products p ON p.product_id = i.product_id
GROUP BY p.product_id, p.product_name ORDER BY SUM(i.qty * i.unit_price) DESC, p.product_id;
END
