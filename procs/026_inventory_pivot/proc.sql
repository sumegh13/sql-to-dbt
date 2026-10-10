CREATE OR ALTER PROCEDURE dbo.usp_inventory_pivot
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.inventory_pivot') IS NOT NULL DROP TABLE dbo.inventory_pivot;
SELECT product_id, ISNULL([A],0) AS wh_a, ISNULL([B],0) AS wh_b INTO dbo.inventory_pivot
FROM (SELECT product_id, warehouse, qty_on_hand FROM dbo.inventory) s PIVOT (SUM(qty_on_hand) FOR warehouse IN ([A],[B])) p;
END
