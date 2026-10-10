CREATE OR ALTER PROCEDURE dbo.usp_random_audit_sample
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.random_audit_sample') IS NOT NULL DROP TABLE dbo.random_audit_sample;
SELECT TOP 5 customer_id, customer_name, NEWID() AS audit_token, GETDATE() AS sampled_at
INTO dbo.random_audit_sample FROM dbo.customers ORDER BY NEWID();
END
