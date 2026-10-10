CREATE OR ALTER PROCEDURE dbo.usp_mom_growth
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.mom_growth') IS NOT NULL DROP TABLE dbo.mom_growth;
WITH m AS (SELECT YEAR(order_date) AS yr, MONTH(order_date) AS mo, SUM(amount) AS rev FROM dbo.orders
           WHERE status NOT IN ('cancelled','returned') GROUP BY YEAR(order_date), MONTH(order_date))
SELECT yr, mo, rev, LAG(rev) OVER (ORDER BY yr, mo) AS prev_rev,
  ROUND((rev - LAG(rev) OVER (ORDER BY yr, mo)) * 100.0 / NULLIF(LAG(rev) OVER (ORDER BY yr, mo), 0), 2) AS growth_pct
INTO dbo.mom_growth FROM m;
END
