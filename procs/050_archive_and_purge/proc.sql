CREATE OR ALTER PROCEDURE dbo.usp_archive_and_purge
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.archive_and_purge') IS NOT NULL DROP TABLE dbo.archive_and_purge;
SELECT * INTO dbo.archive_and_purge FROM dbo.orders WHERE status = 'cancelled' AND order_date < '2025-10-01';
DELETE FROM dbo.orders WHERE order_id IN (SELECT order_id FROM dbo.archive_and_purge);
UPDATE dbo.customers SET is_active = 0 WHERE customer_id NOT IN (SELECT customer_id FROM dbo.orders);
END
