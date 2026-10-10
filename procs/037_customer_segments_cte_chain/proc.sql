CREATE OR ALTER PROCEDURE dbo.usp_customer_segments_cte_chain
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_segments_cte_chain') IS NOT NULL DROP TABLE dbo.customer_segments_cte_chain;
WITH a AS (SELECT order_id, customer_id, amount FROM dbo.orders WHERE status NOT IN ('cancelled','returned')),
b AS (SELECT customer_id, COUNT(*) AS n, SUM(amount) AS s FROM a GROUP BY customer_id),
c AS (SELECT customer_id, n, s, s / n AS avg_amt FROM b),
d AS (SELECT customer_id, n, s, avg_amt, CASE WHEN n >= 3 THEN 'frequent' WHEN n = 2 THEN 'repeat' ELSE 'one_off' END AS segment FROM c)
SELECT * INTO dbo.customer_segments_cte_chain FROM d;
END
