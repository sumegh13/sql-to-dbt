CREATE OR ALTER PROCEDURE dbo.usp_customer_name_cleanup
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_name_cleanup') IS NOT NULL DROP TABLE dbo.customer_name_cleanup;
SELECT customer_id, UPPER(LTRIM(RTRIM(customer_name))) AS clean_name, LEFT(LTRIM(customer_name), 1) AS initial,
  customer_name + ' <' + email + '>' AS display,
  REPLACE(LOWER(RTRIM(LTRIM(customer_name))), ' ', '_') AS slug, LEN(customer_name) AS name_len
INTO dbo.customer_name_cleanup FROM dbo.customers;
END
