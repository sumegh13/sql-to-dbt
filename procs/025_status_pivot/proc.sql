CREATE OR ALTER PROCEDURE dbo.usp_status_pivot
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.status_pivot') IS NOT NULL DROP TABLE dbo.status_pivot;
SELECT customer_id, ISNULL([shipped],0) AS shipped, ISNULL([pending],0) AS pending, ISNULL([cancelled],0) AS cancelled
INTO dbo.status_pivot FROM (SELECT customer_id, status, order_id FROM dbo.orders) src
PIVOT (COUNT(order_id) FOR status IN ([shipped],[pending],[cancelled])) p;
END
