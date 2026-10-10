CREATE OR ALTER PROCEDURE dbo.usp_product_return_rate
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.product_return_rate') IS NOT NULL DROP TABLE dbo.product_return_rate;
SELECT p.product_id, p.product_name, COUNT(*) AS line_count,
  SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS returned_lines,
  CAST(SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS return_rate
INTO dbo.product_return_rate FROM dbo.order_items i JOIN dbo.orders o ON o.order_id = i.order_id
JOIN dbo.products p ON p.product_id = i.product_id GROUP BY p.product_id, p.product_name;
END
