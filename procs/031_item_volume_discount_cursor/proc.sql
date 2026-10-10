CREATE OR ALTER PROCEDURE dbo.usp_item_volume_discount_cursor
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.item_volume_discount_cursor') IS NOT NULL DROP TABLE dbo.item_volume_discount_cursor;
CREATE TABLE dbo.item_volume_discount_cursor (item_id INT, order_id INT, qty INT, running_qty INT, discount_pct INT);
DECLARE @item INT, @ord INT, @q INT, @prev INT = NULL, @run INT = 0;
DECLARE c CURSOR FOR SELECT item_id, order_id, qty FROM dbo.order_items ORDER BY order_id, item_id;
OPEN c; FETCH NEXT FROM c INTO @item, @ord, @q;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @ord SET @run = 0;
    SET @run = @run + @q; SET @prev = @ord;
    INSERT INTO dbo.item_volume_discount_cursor VALUES (@item, @ord, @q, @run, CASE WHEN @run >= 10 THEN 10 WHEN @run >= 5 THEN 5 ELSE 0 END);
    FETCH NEXT FROM c INTO @item, @ord, @q;
END
CLOSE c; DEALLOCATE c;
END
