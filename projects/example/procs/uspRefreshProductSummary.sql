CREATE PROCEDURE dbo.uspRefreshProductSummary
AS
BEGIN
    SET NOCOUNT ON;
    TRUNCATE TABLE dbo.ProductSummary;
    INSERT INTO dbo.ProductSummary (ProductID, ProductName, UnitsSold, Revenue)
    SELECT p.ProductID, p.ProductName, ISNULL(SUM(l.Quantity), 0), ISNULL(SUM(l.Quantity * l.UnitPrice), 0)
    FROM dbo.Products p
    LEFT JOIN Sales.OrderLines l ON l.ProductID = p.ProductID
    GROUP BY p.ProductID, p.ProductName;
END
