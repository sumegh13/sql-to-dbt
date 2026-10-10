CREATE PROCEDURE Sales.uspCustomerLifetime
AS
BEGIN
    SET NOCOUNT ON;
    CREATE TABLE #spend (CustomerID INT, FirstOrder DATE, LastOrder DATE, Revenue DECIMAL(14,2));
    INSERT INTO #spend
    SELECT o.CustomerID, MIN(o.OrderDate), MAX(o.OrderDate), SUM(l.Quantity * l.UnitPrice)
    FROM Sales.Orders o JOIN Sales.OrderLines l ON l.OrderID = o.OrderID
    WHERE o.Status IN ('shipped', 'closed')
    GROUP BY o.CustomerID;

    SELECT c.CustomerID, c.CustomerName,
           ISNULL(s.Revenue, 0) AS Revenue,
           DATEDIFF(month, s.FirstOrder, s.LastOrder) AS TenureMonths,
           CASE WHEN s.Revenue IS NULL THEN 'none'
                WHEN s.Revenue >= 2000 THEN 'high'
                WHEN s.Revenue >= 500 THEN 'mid' ELSE 'low' END AS Segment
    FROM dbo.Customers c LEFT JOIN #spend s ON s.CustomerID = c.CustomerID;
END
