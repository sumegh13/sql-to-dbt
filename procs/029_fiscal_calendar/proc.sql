CREATE OR ALTER PROCEDURE dbo.usp_fiscal_calendar
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.fiscal_calendar') IS NOT NULL DROP TABLE dbo.fiscal_calendar;
SELECT order_id, order_date, EOMONTH(order_date) AS month_end,
  CASE WHEN MONTH(order_date) >= 4 THEN YEAR(order_date) + 1 ELSE YEAR(order_date) END AS fiscal_year,
  ((MONTH(order_date) + 8) % 12) / 3 + 1 AS fiscal_qtr,
  DATENAME(weekday, order_date) AS dow
INTO dbo.fiscal_calendar FROM dbo.orders;
END
