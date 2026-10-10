"""Generate the shared legacy-DB fixture (corpus/fixture.sql + corpus/tables.json).

Data deliberately includes traps a naive translation trips on: mixed-case status values
(SQL Server default collation is case-insensitive), NULL regions/emails, padded names,
non-numeric codes, short VARCHAR columns (ISNULL truncation), decimals.
"""
import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

random.seed(7)
OUT = Path(__file__).parent

SCHEMA = {
    "customers": "customer_id INT, customer_name VARCHAR(100), region VARCHAR(10) NULL, signup_date DATE, email VARCHAR(100) NULL, is_active BIT, legacy_code VARCHAR(10) NULL, tags VARCHAR(100) NULL",
    "products": "product_id INT, product_name VARCHAR(50), category VARCHAR(20), unit_price DECIMAL(18,2)",
    "orders": "order_id INT, customer_id INT, order_date DATE, amount DECIMAL(18,2), status VARCHAR(20)",
    "order_items": "item_id INT, order_id INT, product_id INT, qty INT, unit_price DECIMAL(18,2)",
    "employees": "employee_id INT, emp_name VARCHAR(50), manager_id INT NULL, department VARCHAR(20), salary DECIMAL(18,2), hire_date DATE",
    "payments": "payment_id INT, order_id INT, paid_amount DECIMAL(18,2), paid_date DATE, method VARCHAR(10)",
    "inventory": "product_id INT, warehouse VARCHAR(5), qty_on_hand INT",
    "price_history": "product_id INT, effective_date DATE, price DECIMAL(18,2)",
    "customer_staging": "customer_id INT, customer_name VARCHAR(100), region VARCHAR(10) NULL, email VARCHAR(100) NULL",
    "report_config": "table_name VARCHAR(50), filter_col VARCHAR(50)",
}


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, Decimal)):
        return str(v)
    if isinstance(v, date):
        return f"'{v.isoformat()}'"
    return "'" + str(v).replace("'", "''") + "'"


def D(x):
    return Decimal(str(round(x, 2)))


names = ["Acme Corp", "Globex", "Initech", "Hooli", "  Umbrella ", "Stark Industries", "Wayne Enterprises",
         "Wonka", "Cyberdyne", "Soylent", "Tyrell", "Massive Dynamic"]
regions = ["East", "West", None, "North", "South", "East", "West", "East", "North", None, "South", "West"]
domains = ["acme.com", "globex.io", "example.org"]
codes = ["100", "A1", "007", None, "x9", "250", "12", "B2", None, "300", "45", "Z"]
tags = ["vip, eu", None, "new", "vip,us, b2b", None, "b2b", "eu", "vip", None, "us", "b2b,eu", "new, vip"]

customers = []
for i, n in enumerate(names, 1):
    email = None if i in (4, 9) else f"{n.strip().split()[0].lower()}@{domains[i % 3]}"
    customers.append((i, n, regions[i - 1], date(2024, 1, 1) + timedelta(days=37 * i), email, 0 if i in (6, 11) else 1, codes[i - 1], tags[i - 1]))

cats = ["Hardware", "Software", "Services"]
products = [(p, f"Product {chr(64 + p)}", cats[p % 3], D(random.choice([9.99, 19.5, 49, 120, 15.25, 5, 75.5, 300, 8.75, 60]))) for p in range(1, 11)]

orders, items = [], []
status_pool = ["shipped"] * 6 + ["Shipped", "SHIPPED", "cancelled", "Cancelled", "pending", "pending", "returned"]
forced = [(1, date(2025, 11, 10)), (1, date(2025, 11, 11)), (1, date(2025, 11, 12))]
iid = 1
for oid in range(1, 35):
    cust, dt = forced[oid - 1] if oid <= len(forced) else (random.randint(1, 10), date(2025, 9, 1) + timedelta(days=random.randint(0, 120)))
    total = Decimal("0.00")
    for _ in range(random.randint(1, 3)):
        p = random.choice(products)
        q = random.randint(1, 4)
        items.append((iid, oid, p[0], q, p[3]))
        total += q * p[3]
        iid += 1
    orders.append((oid, cust, dt, total, random.choice(status_pool)))

payments, pid = [], 1
for o in orders:
    if o[4].lower() in ("cancelled", "pending") or random.random() < 0.3:
        continue
    if random.random() < 0.4:
        half = (o[3] / 2).quantize(Decimal("0.01"))
        payments.append((pid, o[0], half, o[2] + timedelta(days=3), "card")); pid += 1
        payments.append((pid, o[0], half if random.random() < 0.5 else o[3] - half, o[2] + timedelta(days=9), "wire")); pid += 1
    else:
        payments.append((pid, o[0], o[3], o[2] + timedelta(days=2), "card")); pid += 1

inventory = [(p[0], w, random.randint(0, 60)) for p in products for w in ("A", "B") if not (p[0] == 10 and w == "B")]
price_history = []
for p in products:
    price = p[3]
    for k in range(random.randint(1, 3)):
        price_history.append((p[0], date(2024, 1, 1) + timedelta(days=150 * k), D(float(price) * (1 + 0.07 * k))))

emp = [(1, "Ada", None, "Exec", 250000), (2, "Bob", 1, "Eng", 150000), (3, "Cy", 1, "Sales", 120000),
       (4, "Di", 2, "Eng", 110000), (5, "Eli", 2, "Eng", 110000), (6, "Fay", 3, "Sales", 70000),
       (7, "Gus", 3, "Sales", 65000), (8, "Hal", 4, "Eng", 69999), (9, "Ivy", 4, "Eng", 90000), (10, "Jo", 6, "Sales", 50000)]
employees = [(e[0], e[1], e[2], e[3], D(e[4]), date(2018, 1, 1) + timedelta(days=200 * e[0])) for e in emp]

staging = [(2, "Globex Intl", None, None), (5, "Umbrella Corp", "East", "umbrella@globex.io"),
           (13, "Pied Piper", "West", "pp@example.org"), (14, "Aviato", "North", None), (7, "Wayne Ent", "South", "w@acme.com")]
report_config = [("customers", "email")]

DATA = dict(customers=customers, products=products, orders=orders, order_items=items, employees=employees,
            payments=payments, inventory=inventory, price_history=price_history, customer_staging=staging,
            report_config=report_config)

lines = []
for t, ddl in SCHEMA.items():
    lines.append(f"IF OBJECT_ID('dbo.{t}') IS NOT NULL DROP TABLE dbo.{t};")
lines.append("GO")
for t, ddl in SCHEMA.items():
    lines.append(f"CREATE TABLE dbo.{t} ({ddl});")
lines.append("GO")
for t, rows in DATA.items():
    for i in range(0, len(rows), 50):
        chunk = rows[i:i + 50]
        lines.append(f"INSERT INTO dbo.{t} VALUES " + ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in chunk) + ";")
(OUT / "fixture.sql").write_text("\n".join(lines) + "\n")
(OUT / "tables.json").write_text(json.dumps(["dbo." + t for t in SCHEMA], indent=1))
print({t: len(r) for t, r in DATA.items()})
