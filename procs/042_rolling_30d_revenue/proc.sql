CREATE OR ALTER PROCEDURE dbo.usp_rolling_30d_revenue
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.rolling_30d_revenue') IS NOT NULL DROP TABLE dbo.rolling_30d_revenue;
SELECT d.order_date,
  (SELECT SUM(o2.amount) FROM dbo.orders o2 WHERE o2.order_date > DATEADD(day, -30, d.order_date) AND o2.order_date <= d.order_date
     AND o2.status NOT IN ('cancelled','returned')) AS rolling_30d
INTO dbo.rolling_30d_revenue FROM (SELECT DISTINCT order_date FROM dbo.orders) d;
END
