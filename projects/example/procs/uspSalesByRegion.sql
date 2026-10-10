CREATE PROCEDURE Sales.uspSalesByRegion
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    SELECT ISNULL(c.Region, 'Unassigned') AS Region,
           COUNT(DISTINCT o.OrderID) AS Orders,
           SUM(l.Quantity * l.UnitPrice) AS GrossRevenue
    FROM Sales.Orders o
    JOIN dbo.Customers c ON c.CustomerID = o.CustomerID
    JOIN Sales.OrderLines l ON l.OrderID = o.OrderID
    WHERE o.OrderDate BETWEEN @StartDate AND @EndDate
      AND o.Status <> 'cancelled'
    GROUP BY ISNULL(c.Region, 'Unassigned');
END
