CREATE OR ALTER PROCEDURE dbo.usp_latest_product_price
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.latest_product_price') IS NOT NULL DROP TABLE dbo.latest_product_price;
WITH r AS (
  SELECT product_id, price, effective_date, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_date DESC) AS rn
  FROM dbo.price_history WHERE effective_date <= '2025-12-31')
SELECT product_id, price, effective_date INTO dbo.latest_product_price FROM r WHERE rn = 1;
END
