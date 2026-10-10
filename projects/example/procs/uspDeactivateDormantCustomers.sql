CREATE PROCEDURE dbo.uspDeactivateDormantCustomers
    @AsOfDate DATE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE c SET Status = 'inactive'
    FROM dbo.Customers c
    WHERE NOT EXISTS (SELECT 1 FROM Sales.Orders o WHERE o.CustomerID = c.CustomerID AND o.OrderDate >= DATEADD(day, -180, @AsOfDate));
    SELECT CustomerID, CustomerName, Status FROM dbo.Customers WHERE Status = 'inactive';
END
