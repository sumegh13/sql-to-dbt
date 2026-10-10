CREATE PROCEDURE Sales.uspTopProducts
    @TopN INT = 5,
    @Category VARCHAR(30) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@TopN) p.ProductID, p.ProductName, p.Category, SUM(l.Quantity) AS UnitsSold
    FROM dbo.Products p
    JOIN Sales.OrderLines l ON l.ProductID = p.ProductID
    WHERE @Category IS NULL OR p.Category = @Category
    GROUP BY p.ProductID, p.ProductName, p.Category
    ORDER BY SUM(l.Quantity) DESC, p.ProductID;
END
