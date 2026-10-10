CREATE OR ALTER PROCEDURE dbo.usp_customer_email_domains
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_email_domains') IS NOT NULL DROP TABLE dbo.customer_email_domains;
SELECT SUBSTRING(email, CHARINDEX('@',email)+1, LEN(email)) AS domain, COUNT(*) AS customers INTO dbo.customer_email_domains
FROM dbo.customers WHERE email IS NOT NULL GROUP BY SUBSTRING(email, CHARINDEX('@',email)+1, LEN(email));
END
