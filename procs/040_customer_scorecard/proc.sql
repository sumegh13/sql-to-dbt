CREATE OR ALTER PROCEDURE dbo.usp_customer_scorecard
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_scorecard') IS NOT NULL DROP TABLE dbo.customer_scorecard;
SELECT c.customer_id,
  SUM(CASE WHEN o.status = 'shipped' THEN o.amount ELSE 0 END) AS shipped_amt,
  SUM(CASE WHEN o.status = 'pending' THEN o.amount ELSE 0 END) AS pending_amt,
  SUM(CASE WHEN o.status = 'cancelled' THEN o.amount ELSE 0 END) AS cancelled_amt,
  MAX(o.order_date) AS last_order, COUNT(o.order_id) AS orders
INTO dbo.customer_scorecard FROM dbo.customers c LEFT JOIN dbo.orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;
END
