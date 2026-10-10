CREATE OR ALTER PROCEDURE dbo.usp_cancel_pct_int_division
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.cancel_pct_int_division') IS NOT NULL DROP TABLE dbo.cancel_pct_int_division;
SELECT customer_id, COUNT(*) AS total_orders,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) * 100 / COUNT(*) AS cancel_pct
INTO dbo.cancel_pct_int_division FROM dbo.orders GROUP BY customer_id;
END
