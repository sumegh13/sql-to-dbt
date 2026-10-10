CREATE OR ALTER PROCEDURE dbo.usp_customer_tags_split
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.customer_tags_split') IS NOT NULL DROP TABLE dbo.customer_tags_split;
SELECT c.customer_id, LTRIM(RTRIM(s.value)) AS tag INTO dbo.customer_tags_split FROM dbo.customers c
CROSS APPLY STRING_SPLIT(c.tags, ',') s WHERE c.tags IS NOT NULL;
END
