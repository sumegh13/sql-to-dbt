CREATE OR ALTER PROCEDURE dbo.usp_inventory_low_stock
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.inventory_low_stock') IS NOT NULL DROP TABLE dbo.inventory_low_stock;
SELECT p.product_id, p.product_name, SUM(inv.qty_on_hand) AS total_qty,
  IIF(SUM(inv.qty_on_hand) < 20, 1, 0) AS low_stock
INTO dbo.inventory_low_stock FROM dbo.products p LEFT JOIN dbo.inventory inv ON inv.product_id = p.product_id
GROUP BY p.product_id, p.product_name;
END
