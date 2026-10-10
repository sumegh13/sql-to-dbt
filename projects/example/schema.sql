CREATE SCHEMA Sales;
GO
CREATE TABLE dbo.Customers (
    CustomerID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerName NVARCHAR(100) NOT NULL,
    Region VARCHAR(20) NULL,
    Status VARCHAR(20) NOT NULL DEFAULT 'active',
    CreatedAt DATETIME NOT NULL
);
CREATE TABLE dbo.Products (
    ProductID INT IDENTITY(1,1) PRIMARY KEY,
    ProductName NVARCHAR(100) NOT NULL,
    Category VARCHAR(30) NOT NULL,
    ListPrice DECIMAL(12,2) NOT NULL
);
CREATE TABLE Sales.Orders (
    OrderID INT IDENTITY(1,1) PRIMARY KEY,
    CustomerID INT NOT NULL REFERENCES dbo.Customers(CustomerID),
    OrderDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL
);
CREATE TABLE Sales.OrderLines (
    OrderLineID INT IDENTITY(1,1) PRIMARY KEY,
    OrderID INT NOT NULL REFERENCES Sales.Orders(OrderID),
    ProductID INT NOT NULL REFERENCES dbo.Products(ProductID),
    Quantity INT NOT NULL,
    UnitPrice DECIMAL(12,2) NOT NULL,
    Discount DECIMAL(4,2) NULL
);
CREATE TABLE dbo.ProductSummary (
    ProductID INT NOT NULL,
    ProductName NVARCHAR(100) NOT NULL,
    UnitsSold INT NOT NULL,
    Revenue DECIMAL(14,2) NOT NULL
);
