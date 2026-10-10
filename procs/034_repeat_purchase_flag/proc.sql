CREATE OR ALTER PROCEDURE dbo.usp_repeat_purchase_flag
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.repeat_purchase_flag') IS NOT NULL DROP TABLE dbo.repeat_purchase_flag;
SELECT order_id, customer_id, order_date,
  LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS prev_date,
  CASE WHEN DATEDIFF(day, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id), order_date) <= 7 THEN 1 ELSE 0 END AS is_repeat_7d
INTO dbo.repeat_purchase_flag FROM dbo.orders;
END
