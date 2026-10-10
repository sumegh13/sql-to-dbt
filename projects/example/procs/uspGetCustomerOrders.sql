CREATE PROCEDURE Sales.uspGetCustomerOrders
    @CustomerID INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT o.OrderID, o.OrderDate, o.Status,
           SUM(l.Quantity * l.UnitPrice * (1 - ISNULL(l.Discount, 0))) AS OrderTotal,
           COUNT(*) AS LineCount
    FROM Sales.Orders o
    JOIN Sales.OrderLines l ON l.OrderID = o.OrderID
    WHERE o.CustomerID = @CustomerID
    GROUP BY o.OrderID, o.OrderDate, o.Status;
END
