CREATE OR ALTER PROCEDURE dbo.usp_payment_balance_cursor
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.payment_balance_cursor') IS NOT NULL DROP TABLE dbo.payment_balance_cursor;
CREATE TABLE dbo.payment_balance_cursor (payment_id INT, order_id INT, paid_amount DECIMAL(18,2), cumulative_paid DECIMAL(18,2), balance_after DECIMAL(18,2), overpaid INT);
DECLARE @pid INT, @oid INT, @paid DECIMAL(18,2), @amt DECIMAL(18,2), @prev INT = NULL, @cum DECIMAL(18,2) = 0;
DECLARE c CURSOR FOR SELECT p.payment_id, p.order_id, p.paid_amount, o.amount FROM dbo.payments p JOIN dbo.orders o ON o.order_id = p.order_id
  ORDER BY p.order_id, p.paid_date, p.payment_id;
OPEN c; FETCH NEXT FROM c INTO @pid, @oid, @paid, @amt;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @oid SET @cum = 0;
    SET @cum = @cum + @paid; SET @prev = @oid;
    INSERT INTO dbo.payment_balance_cursor VALUES (@pid, @oid, @paid, @cum, @amt - @cum, CASE WHEN @cum > @amt THEN 1 ELSE 0 END);
    FETCH NEXT FROM c INTO @pid, @oid, @paid, @amt;
END
CLOSE c; DEALLOCATE c;
END
