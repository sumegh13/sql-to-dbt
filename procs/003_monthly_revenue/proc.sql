CREATE OR ALTER PROCEDURE dbo.usp_monthly_revenue
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.monthly_revenue') IS NOT NULL DROP TABLE dbo.monthly_revenue;
SELECT YEAR(order_date) AS yr, MONTH(order_date) AS mo, SUM(amount) AS revenue INTO dbo.monthly_revenue
FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY YEAR(order_date), MONTH(order_date);
END
