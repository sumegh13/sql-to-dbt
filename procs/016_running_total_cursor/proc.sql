CREATE OR ALTER PROCEDURE dbo.usp_running_total_cursor
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.running_total_cursor') IS NOT NULL DROP TABLE dbo.running_total_cursor;
CREATE TABLE dbo.running_total_cursor (customer_id INT, order_id INT, order_date DATE, amount DECIMAL(18,2), running_total DECIMAL(18,2));
DECLARE @cust INT, @oid INT, @dt DATE, @amt DECIMAL(18,2), @prev INT = NULL, @run DECIMAL(18,2) = 0;
DECLARE c CURSOR FOR SELECT customer_id, order_id, order_date, amount FROM dbo.orders ORDER BY customer_id, order_date, order_id;
OPEN c; FETCH NEXT FROM c INTO @cust, @oid, @dt, @amt;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @cust SET @run = 0;
    SET @run = @run + @amt; SET @prev = @cust;
    INSERT INTO dbo.running_total_cursor VALUES (@cust, @oid, @dt, @amt, @run);
    FETCH NEXT FROM c INTO @cust, @oid, @dt, @amt;
END
CLOSE c; DEALLOCATE c;
END
