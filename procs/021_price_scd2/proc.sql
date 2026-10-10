CREATE OR ALTER PROCEDURE dbo.usp_price_scd2
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.price_scd2') IS NOT NULL DROP TABLE dbo.price_scd2;
SELECT product_id, price, effective_date AS valid_from,
  ISNULL(LEAD(effective_date) OVER (PARTITION BY product_id ORDER BY effective_date), '9999-12-31') AS valid_to,
  CASE WHEN LEAD(effective_date) OVER (PARTITION BY product_id ORDER BY effective_date) IS NULL THEN 1 ELSE 0 END AS is_current
INTO dbo.price_scd2 FROM dbo.price_history;
END
