CREATE OR ALTER PROCEDURE dbo.usp_customer_order_totals
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_order_totals') IS NOT NULL DROP TABLE dbo.customer_order_totals;
CREATE TABLE dbo.customer_order_totals (customer_id INT, customer_name VARCHAR(100), order_count INT, total_amount DECIMAL(18,2), tier VARCHAR(10));
DECLARE @id INT, @name VARCHAR(100), @cnt INT, @amt DECIMAL(18,2);
DECLARE c CURSOR FOR SELECT customer_id, customer_name FROM dbo.customers;
OPEN c; FETCH NEXT FROM c INTO @id, @name;
WHILE @@FETCH_STATUS = 0
BEGIN
    SELECT @cnt = COUNT(*), @amt = ISNULL(SUM(amount),0) FROM dbo.orders WHERE customer_id=@id AND status<>'cancelled';
    INSERT INTO dbo.customer_order_totals VALUES (@id,@name,@cnt,@amt,
        CASE WHEN @amt>=1000 THEN 'gold' WHEN @amt>=500 THEN 'silver' ELSE 'bronze' END);
    FETCH NEXT FROM c INTO @id, @name;
END
CLOSE c; DEALLOCATE c;
END
