CREATE OR ALTER PROCEDURE dbo.usp_dynamic_sql_report
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.dynamic_sql_report') IS NOT NULL DROP TABLE dbo.dynamic_sql_report;
DECLARE @tbl SYSNAME, @col SYSNAME, @sql NVARCHAR(MAX);
SELECT TOP 1 @tbl = table_name, @col = filter_col FROM dbo.report_config;
SET @sql = N'SELECT * INTO dbo.dynamic_sql_report FROM dbo.' + QUOTENAME(@tbl) + N' WHERE ' + QUOTENAME(@col) + N' IS NOT NULL';
EXEC sp_executesql @sql;
END
