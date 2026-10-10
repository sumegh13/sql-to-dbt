CREATE OR ALTER PROCEDURE dbo.usp_order_rank_per_customer
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.order_rank_per_customer') IS NOT NULL DROP TABLE dbo.order_rank_per_customer;
SELECT order_id, customer_id, amount,
  ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC, order_id) AS rn,
  RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk,
  DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS drnk
INTO dbo.order_rank_per_customer FROM dbo.orders;
END
