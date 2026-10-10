CREATE OR ALTER PROCEDURE dbo.usp_order_outstanding_update_join
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.order_outstanding_update_join') IS NOT NULL DROP TABLE dbo.order_outstanding_update_join;
SELECT o.order_id, o.amount, CAST(0 AS DECIMAL(18,2)) AS paid, CAST(NULL AS DATE) AS last_paid INTO #t FROM dbo.orders o;
UPDATE t SET paid = x.total, last_paid = x.last_dt FROM #t t
JOIN (SELECT order_id, SUM(paid_amount) AS total, MAX(paid_date) AS last_dt FROM dbo.payments GROUP BY order_id) x ON x.order_id = t.order_id;
SELECT order_id, amount, paid, amount - paid AS outstanding, last_paid INTO dbo.order_outstanding_update_join FROM #t;
END
