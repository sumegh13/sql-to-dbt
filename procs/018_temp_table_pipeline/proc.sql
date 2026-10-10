CREATE OR ALTER PROCEDURE dbo.usp_temp_table_pipeline
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.temp_table_pipeline') IS NOT NULL DROP TABLE dbo.temp_table_pipeline;
SELECT customer_id, SUM(amount) AS spend INTO #spend FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY customer_id;
SELECT c.customer_id, c.customer_name, ISNULL(s.spend, 0) AS spend INTO #joined FROM dbo.customers c LEFT JOIN #spend s ON s.customer_id = c.customer_id;
SELECT j.customer_id, j.customer_name, j.spend,
  CASE WHEN j.spend > (SELECT AVG(spend) FROM #joined) THEN 'above_avg' ELSE 'at_or_below_avg' END AS vs_avg
INTO dbo.temp_table_pipeline FROM #joined j;
END
