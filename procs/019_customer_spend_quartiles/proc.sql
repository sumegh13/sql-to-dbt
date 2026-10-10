CREATE OR ALTER PROCEDURE dbo.usp_customer_spend_quartiles
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_spend_quartiles') IS NOT NULL DROP TABLE dbo.customer_spend_quartiles;
WITH s AS (SELECT customer_id, SUM(amount) AS spend FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY customer_id)
SELECT customer_id, spend, NTILE(4) OVER (ORDER BY spend DESC, customer_id) AS quartile
INTO dbo.customer_spend_quartiles FROM s;
END
