CREATE OR ALTER PROCEDURE dbo.usp_legacy_code_cleanup
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.legacy_code_cleanup') IS NOT NULL DROP TABLE dbo.legacy_code_cleanup;
SELECT customer_id, legacy_code, TRY_CAST(legacy_code AS INT) AS legacy_code_num,
  IIF(TRY_CAST(legacy_code AS INT) IS NULL, 1, 0) AS invalid
INTO dbo.legacy_code_cleanup FROM dbo.customers;
END
