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

def random_data(seed):
    random.seed(seed)
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

    return dict(customers=customers, products=products, orders=orders, order_items=items, employees=employees,
                payments=payments, inventory=inventory, price_history=price_history, customer_staging=staging,
                report_config=report_config)



def edge_data():
    """Hand-built edge cases. Natural keys stay unique so every proc stays deterministic."""
    d = date
    customers = [
        (1, "Edge Boundary", "East", d(2024, 2, 29), "edge@acme.com", 1, "", "vip,"),          # '' -> TRY_CAST gives 0 in T-SQL
        (2, "Trailing   ", "West", d(2024, 3, 1), "noatsign", 1, " 12", "a,,b"),              # email without '@'
        (3, "  Leading", None, d(2024, 3, 2), None, 0, "1.5", None),
        (4, "Only Cancelled", "Southwest_", d(2024, 3, 3), "oc@example.org", 1, "-7", "b2b"),  # region exactly 10 chars
        (5, "No Orders", None, d(2024, 3, 4), "no@example.org", 1, "2147483648", " eu "),      # int overflow code
        (6, "Refunder", "North", d(2024, 3, 5), "ref@globex.io", 0, "0", "vip, us"),
        (7, "Ties", "South", d(2024, 3, 6), "ties@globex.io", 1, None, ""),
    ]
    products = [(1, "Alpha", "Hardware", D(500)), (2, "Beta", "Software", D(0)), (3, "Gamma", "Services", D(0.01)),
                (4, "Delta", "Hardware", D(333.33)), (5, "Unsold", "Software", D(10))]
    orders = [
        (1, 1, d(2025, 12, 31), D(500), "shipped"),        # silver boundary exactly
        (2, 1, d(2026, 1, 1), D(500), "Shipped "),        # trailing space + year rollover -> total 1000 gold boundary
        (3, 2, d(2025, 11, 30), None, "shipped"),         # NULL amount
        (4, 2, d(2025, 12, 1), D(100), None),             # NULL status
        (5, 2, d(2025, 12, 2), D(0), "pending"),
        (6, 4, d(2025, 10, 15), D(250), "CANCELLED"),
        (7, 4, d(2025, 9, 1), D(250), "cancelled"),
        (8, 6, d(2025, 11, 5), D(-50), "returned"),       # refund
        (9, 6, d(2025, 11, 5), D(75.5), "shipped"),       # same customer, same day
        (10, 7, d(2025, 12, 10), D(99.99), "shipped"),    # three-way amount tie
        (11, 7, d(2025, 12, 11), D(99.99), "pending"),
        (12, 7, d(2025, 12, 12), D(99.99), "shipped"),
        (13, 99, d(2025, 12, 20), D(42), "shipped"),      # orphan customer
        (14, 3, d(2024, 2, 29), D(0.01), "shipped"),      # leap day, very old
        (15, 3, d(2025, 1, 31), D(1999.99), "shipped"),   # large value, old date
    ]
    items = [(1, 1, 1, 1, D(500)), (2, 2, 1, 1, D(500)), (3, 3, 2, 3, D(0)), (4, 4, 3, 0, D(0.01)), (5, 4, 4, 1, D(333.33)),
             (6, 5, 2, 1, D(0)), (7, 6, 4, 2, D(125)), (8, 7, 4, 1, D(250)), (9, 8, 3, 5, D(-10)), (10, 9, 1, 1, D(75.5)),
             (11, 10, 1, 4, D(25)), (12, 10, 1, 6, D(25)), (13, 10, 2, 1, D(0)), (14, 11, 3, 9, D(11.11)),
             (15, 12, 4, 1, D(99.99)), (16, 13, 2, 2, D(21)), (17, 14, 3, 1, D(0.01)), (18, 15, 1, 4, D(500))]
    payments = [(1, 1, D(500), d(2026, 1, 2), "card"), (2, 2, D(300), d(2026, 1, 3), "card"), (3, 2, D(300), d(2026, 1, 3), "wire"),  # overpaid, same date
                (4, 3, None, d(2025, 12, 1), "card"), (5, 3, D(10), d(2025, 12, 2), "card"),                                   # NULL payment
                (6, 9, D(0), d(2025, 11, 6), "card"), (7, 12, D(50), d(2025, 12, 13), "wire"), (8, 77, D(5), d(2025, 12, 1), "card")]  # orphan
    inventory = [(1, "A", 20), (1, "B", 0), (2, "B", 19), (3, "A", -5), (4, "A", 10), (4, "B", 9)]  # 5 has none
    price_history = [(1, d(2024, 1, 1), D(450)), (1, d(2025, 12, 31), D(500)), (1, d(2026, 6, 1), D(550)),  # future price
                     (2, d(2025, 1, 1), D(0)), (4, d(2026, 2, 1), D(333.33))]                                  # only-future product
    employees = [(1, "Root", None, "Exec", D(120000), d(2015, 1, 1)), (2, "Root2", None, "Ops", D(70000), d(2016, 1, 1)),
                 (3, "Tie A", 1, "Eng", D(70000), d(2017, 1, 1)), (4, "Tie B", 1, "Eng", D(70000), d(2017, 1, 2)),
                 (5, "Deep", 3, "Eng", D(69999.99), d(2018, 1, 1)), (6, "Deeper", 5, "Eng", D(1), d(2019, 1, 1))]
    staging = [(1, "Edge Renamed", None, None), (6, "Refunder", "North", "new@globex.io"), (8, "Brand New", None, None)]
    return dict(customers=customers, products=products, orders=orders, order_items=items, employees=employees,
                payments=payments, inventory=inventory, price_history=price_history, customer_staging=staging,
                report_config=[("customers", "email")])


def write_sql(name, data):
    lines = []
    for t, ddl in SCHEMA.items():
        lines.append(f"IF OBJECT_ID('dbo.{t}') IS NOT NULL DROP TABLE dbo.{t};")
    lines.append("GO")
    for t, ddl in SCHEMA.items():
        lines.append(f"CREATE TABLE dbo.{t} ({ddl});")
    lines.append("GO")
    for t, rows in data.items():
        for i in range(0, len(rows), 50):
            chunk = rows[i:i + 50]
            lines.append(f"INSERT INTO dbo.{t} VALUES " + ",".join("(" + ",".join(lit(v) for v in r) + ")" for r in chunk) + ";")
    (OUT / "fixtures").mkdir(exist_ok=True)
    (OUT / "fixtures" / f"{name}.sql").write_text("\n".join(lines) + "\n")
    print(name, {t: len(r) for t, r in data.items()})


# base is the original development fixture; seeds add random variety; edge adds hand-built traps
VARIANTS = {"base": lambda: random_data(7), "seed_101": lambda: random_data(101), "seed_202": lambda: random_data(202), "edge": edge_data}

if __name__ == "__main__":
    for name, make in VARIANTS.items():
        write_sql(name, make())
    (OUT / "tables.json").write_text(json.dumps(["dbo." + t for t in SCHEMA], indent=1))
    (OUT / "variants.json").write_text(json.dumps(list(VARIANTS)))
