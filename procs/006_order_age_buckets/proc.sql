CREATE OR ALTER PROCEDURE dbo.usp_order_age_buckets
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.order_age_buckets') IS NOT NULL DROP TABLE dbo.order_age_buckets;
SELECT order_id, DATEDIFF(day, order_date, '2025-12-31') AS age_days,
  CASE WHEN DATEDIFF(day, order_date, '2025-12-31') <= 30 THEN '0-30'
       WHEN DATEDIFF(day, order_date, '2025-12-31') <= 90 THEN '31-90' ELSE '90+' END AS bucket
INTO dbo.order_age_buckets FROM dbo.orders;
END
