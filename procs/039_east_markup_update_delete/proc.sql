CREATE OR ALTER PROCEDURE dbo.usp_east_markup_update_delete
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.east_markup_update_delete') IS NOT NULL DROP TABLE dbo.east_markup_update_delete;
SELECT order_id, customer_id, amount, status INTO #o FROM dbo.orders;
UPDATE o SET amount = o.amount * 1.1 FROM #o o JOIN dbo.customers c ON c.customer_id = o.customer_id WHERE c.region = 'East';
DELETE FROM #o WHERE status = 'cancelled';
SELECT * INTO dbo.east_markup_update_delete FROM #o;
END
