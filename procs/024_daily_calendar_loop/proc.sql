CREATE OR ALTER PROCEDURE dbo.usp_daily_calendar_loop
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.daily_calendar_loop') IS NOT NULL DROP TABLE dbo.daily_calendar_loop;
CREATE TABLE dbo.daily_calendar_loop (cal_date DATE, orders_placed INT);
DECLARE @d DATE = '2025-11-01';
WHILE @d <= '2025-12-31'
BEGIN
    INSERT INTO dbo.daily_calendar_loop SELECT @d, COUNT(*) FROM dbo.orders WHERE order_date = @d;
    SET @d = DATEADD(day, 1, @d);
END
END
