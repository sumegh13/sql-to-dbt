CREATE OR ALTER PROCEDURE dbo.usp_customer_first_last_order
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_first_last_order') IS NOT NULL DROP TABLE dbo.customer_first_last_order;
SELECT DISTINCT customer_id,
  FIRST_VALUE(order_id) OVER (PARTITION BY customer_id ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_order,
  LAST_VALUE(order_id) OVER (PARTITION BY customer_id ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_order
INTO dbo.customer_first_last_order FROM dbo.orders;
END
