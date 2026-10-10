CREATE OR ALTER PROCEDURE dbo.usp_payment_status
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.payment_status') IS NOT NULL DROP TABLE dbo.payment_status;
SELECT o.order_id, o.amount, ISNULL(SUM(p.paid_amount),0) AS paid,
  CASE WHEN ISNULL(SUM(p.paid_amount),0) >= o.amount THEN 'paid'
       WHEN ISNULL(SUM(p.paid_amount),0) > 0 THEN 'partial' ELSE 'unpaid' END AS payment_status
INTO dbo.payment_status FROM dbo.orders o LEFT JOIN dbo.payments p ON p.order_id = o.order_id
GROUP BY o.order_id, o.amount;
END
