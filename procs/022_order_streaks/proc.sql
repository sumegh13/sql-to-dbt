CREATE OR ALTER PROCEDURE dbo.usp_order_streaks
AS
BEGIN
    SET NOCOUNT ON;
    IF OBJECT_ID('dbo.order_streaks') IS NOT NULL DROP TABLE dbo.order_streaks;
WITH d AS (SELECT DISTINCT customer_id, order_date FROM dbo.orders),
g AS (SELECT customer_id, order_date,
        DATEADD(day, -ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date), order_date) AS grp FROM d)
SELECT customer_id, MIN(order_date) AS streak_start, MAX(order_date) AS streak_end, COUNT(*) AS days
INTO dbo.order_streaks FROM g GROUP BY customer_id, grp;
END
