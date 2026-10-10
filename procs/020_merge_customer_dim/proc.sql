CREATE OR ALTER PROCEDURE dbo.usp_merge_customer_dim
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.merge_customer_dim') IS NOT NULL DROP TABLE dbo.merge_customer_dim;
SELECT customer_id, customer_name, region, email INTO #tgt FROM dbo.customers;
MERGE #tgt AS t USING dbo.customer_staging AS s ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET customer_name = s.customer_name, region = s.region, email = ISNULL(s.email, t.email)
WHEN NOT MATCHED BY TARGET THEN INSERT (customer_id, customer_name, region, email) VALUES (s.customer_id, s.customer_name, s.region, s.email);
SELECT * INTO dbo.merge_customer_dim FROM #tgt;
END
