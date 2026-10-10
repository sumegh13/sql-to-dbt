CREATE OR ALTER PROCEDURE dbo.usp_avg_item_by_category
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.avg_item_by_category') IS NOT NULL DROP TABLE dbo.avg_item_by_category;
SELECT p.category, AVG(i.qty * i.unit_price) AS avg_line_value, COUNT(*) AS line_count INTO dbo.avg_item_by_category
FROM dbo.order_items i JOIN dbo.products p ON p.product_id = i.product_id GROUP BY p.category;
END
