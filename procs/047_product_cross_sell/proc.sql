CREATE OR ALTER PROCEDURE dbo.usp_product_cross_sell
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.product_cross_sell') IS NOT NULL DROP TABLE dbo.product_cross_sell;
SELECT a.product_id AS product_a, b.product_id AS product_b, COUNT(DISTINCT a.order_id) AS together
INTO dbo.product_cross_sell FROM dbo.order_items a JOIN dbo.order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
GROUP BY a.product_id, b.product_id;
END
