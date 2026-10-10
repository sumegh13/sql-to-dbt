"""Proc specs 026-050. Last three (dynamic SQL, nondeterminism, source mutation) have no
reference model on purpose: they are the ones that must be escalated to a human."""

SPECS_B = [
("inventory_pivot", "medium", ["pivot"], r"""
SELECT product_id, ISNULL([A],0) AS wh_a, ISNULL([B],0) AS wh_b INTO dbo.inventory_pivot
FROM (SELECT product_id, warehouse, qty_on_hand FROM dbo.inventory) s PIVOT (SUM(qty_on_hand) FOR warehouse IN ([A],[B])) p;
""", r"""
select product_id,
  coalesce(sum(qty_on_hand) filter (where warehouse = 'A'), 0) as wh_a,
  coalesce(sum(qty_on_hand) filter (where warehouse = 'B'), 0) as wh_b
from <<inventory>> group by product_id
"""),

("largest_order_per_customer", "medium", ["cross-apply", "top-1"], r"""
SELECT c.customer_id, t.order_id, t.amount INTO dbo.largest_order_per_customer FROM dbo.customers c
CROSS APPLY (SELECT TOP 1 o.order_id, o.amount FROM dbo.orders o WHERE o.customer_id = c.customer_id ORDER BY o.amount DESC, o.order_id) t;
""", r"""
select customer_id, order_id, amount from <<orders>>
qualify row_number() over (partition by customer_id order by amount desc, order_id) = 1
"""),

("legacy_code_cleanup", "easy", ["try_cast"], r"""
SELECT customer_id, legacy_code, TRY_CAST(legacy_code AS INT) AS legacy_code_num,
  IIF(TRY_CAST(legacy_code AS INT) IS NULL, 1, 0) AS invalid
INTO dbo.legacy_code_cleanup FROM dbo.customers;
""", r"""
select customer_id, legacy_code, try_cast(legacy_code as integer) as legacy_code_num,
  case when try_cast(legacy_code as integer) is null then 1 else 0 end as invalid
from <<customers>>
"""),

("fiscal_calendar", "medium", ["eomonth", "datename", "modulo"], r"""
SELECT order_id, order_date, EOMONTH(order_date) AS month_end,
  CASE WHEN MONTH(order_date) >= 4 THEN YEAR(order_date) + 1 ELSE YEAR(order_date) END AS fiscal_year,
  ((MONTH(order_date) + 8) % 12) / 3 + 1 AS fiscal_qtr,
  DATENAME(weekday, order_date) AS dow
INTO dbo.fiscal_calendar FROM dbo.orders;
""", r"""
select order_id, order_date, last_day(order_date) as month_end,
  case when month(order_date) >= 4 then year(order_date) + 1 else year(order_date) end as fiscal_year,
  ((month(order_date) + 8) % 12) // 3 + 1 as fiscal_qtr,
  dayname(order_date) as dow
from <<orders>>
"""),

("order_outstanding_update_join", "medium", ["update-from", "temp-tables"], r"""
SELECT o.order_id, o.amount, CAST(0 AS DECIMAL(18,2)) AS paid, CAST(NULL AS DATE) AS last_paid INTO #t FROM dbo.orders o;
UPDATE t SET paid = x.total, last_paid = x.last_dt FROM #t t
JOIN (SELECT order_id, SUM(paid_amount) AS total, MAX(paid_date) AS last_dt FROM dbo.payments GROUP BY order_id) x ON x.order_id = t.order_id;
SELECT order_id, amount, paid, amount - paid AS outstanding, last_paid INTO dbo.order_outstanding_update_join FROM #t;
""", r"""
select o.order_id, o.amount, coalesce(x.total, 0) as paid, o.amount - coalesce(x.total, 0) as outstanding, x.last_dt as last_paid
from <<orders>> o
left join (select order_id, sum(paid_amount) as total, max(paid_date) as last_dt from <<payments>> group by order_id) x
  on x.order_id = o.order_id
"""),

("item_volume_discount_cursor", "hard", ["cursor", "control-break"], r"""
CREATE TABLE dbo.item_volume_discount_cursor (item_id INT, order_id INT, qty INT, running_qty INT, discount_pct INT);
DECLARE @item INT, @ord INT, @q INT, @prev INT = NULL, @run INT = 0;
DECLARE c CURSOR FOR SELECT item_id, order_id, qty FROM dbo.order_items ORDER BY order_id, item_id;
OPEN c; FETCH NEXT FROM c INTO @item, @ord, @q;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @ord SET @run = 0;
    SET @run = @run + @q; SET @prev = @ord;
    INSERT INTO dbo.item_volume_discount_cursor VALUES (@item, @ord, @q, @run, CASE WHEN @run >= 10 THEN 10 WHEN @run >= 5 THEN 5 ELSE 0 END);
    FETCH NEXT FROM c INTO @item, @ord, @q;
END
CLOSE c; DEALLOCATE c;
""", r"""
select item_id, order_id, qty, running_qty,
  case when running_qty >= 10 then 10 when running_qty >= 5 then 5 else 0 end as discount_pct
from (select item_id, order_id, qty,
        cast(sum(qty) over (partition by order_id order by item_id rows between unbounded preceding and current row) as integer) as running_qty
      from <<order_items>>) t
"""),

("customer_first_last_order", "medium", ["first_value", "last_value", "window-frame"], r"""
SELECT DISTINCT customer_id,
  FIRST_VALUE(order_id) OVER (PARTITION BY customer_id ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_order,
  LAST_VALUE(order_id) OVER (PARTITION BY customer_id ORDER BY order_date, order_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_order
INTO dbo.customer_first_last_order FROM dbo.orders;
""", r"""
select distinct customer_id,
  first_value(order_id) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and unbounded following) as first_order,
  last_value(order_id) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and unbounded following) as last_order
from <<orders>>
"""),

("median_order_by_region", "medium", ["percentile_cont"], r"""
SELECT DISTINCT c.region, PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY o.amount) OVER (PARTITION BY c.region) AS median_amount
INTO dbo.median_order_by_region FROM dbo.orders o JOIN dbo.customers c ON c.customer_id = o.customer_id;
""", r"""
select c.region, quantile_cont(cast(o.amount as double), 0.5) as median_amount
from <<orders>> o join <<customers>> c on c.customer_id = o.customer_id group by c.region
"""),

("repeat_purchase_flag", "medium", ["lag", "datediff"], r"""
SELECT order_id, customer_id, order_date,
  LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS prev_date,
  CASE WHEN DATEDIFF(day, LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id), order_date) <= 7 THEN 1 ELSE 0 END AS is_repeat_7d
INTO dbo.repeat_purchase_flag FROM dbo.orders;
""", r"""
select order_id, customer_id, order_date,
  lag(order_date) over (partition by customer_id order by order_date, order_id) as prev_date,
  case when date_diff('day', lag(order_date) over (partition by customer_id order by order_date, order_id), order_date) <= 7 then 1 else 0 end as is_repeat_7d
from <<orders>>
"""),

("mom_growth", "hard", ["lag", "nullif", "decimal-rounding"], r"""
WITH m AS (SELECT YEAR(order_date) AS yr, MONTH(order_date) AS mo, SUM(amount) AS rev FROM dbo.orders
           WHERE status NOT IN ('cancelled','returned') GROUP BY YEAR(order_date), MONTH(order_date))
SELECT yr, mo, rev, LAG(rev) OVER (ORDER BY yr, mo) AS prev_rev,
  ROUND((rev - LAG(rev) OVER (ORDER BY yr, mo)) * 100.0 / NULLIF(LAG(rev) OVER (ORDER BY yr, mo), 0), 2) AS growth_pct
INTO dbo.mom_growth FROM m;
""", r"""
with m as (select year(order_date) as yr, month(order_date) as mo, sum(amount) as rev from <<orders>>
           where lower(status) not in ('cancelled','returned') group by 1, 2)
select yr, mo, rev, lag(rev) over (order by yr, mo) as prev_rev,
  round((rev - lag(rev) over (order by yr, mo)) * 100.0 / nullif(lag(rev) over (order by yr, mo), 0), 2) as growth_pct
from m
"""),

("customer_name_cleanup", "medium", ["string-functions", "null-concat"], r"""
SELECT customer_id, UPPER(LTRIM(RTRIM(customer_name))) AS clean_name, LEFT(LTRIM(customer_name), 1) AS initial,
  customer_name + ' <' + email + '>' AS display,
  REPLACE(LOWER(RTRIM(LTRIM(customer_name))), ' ', '_') AS slug, LEN(customer_name) AS name_len
INTO dbo.customer_name_cleanup FROM dbo.customers;
""", r"""
select customer_id, upper(trim(customer_name)) as clean_name, left(ltrim(customer_name), 1) as initial,
  customer_name || ' <' || email || '>' as display,
  replace(lower(trim(customer_name)), ' ', '_') as slug, length(rtrim(customer_name)) as name_len
from <<customers>>
"""),

("customer_segments_cte_chain", "medium", ["cte-chain", "decimal-division"], r"""
WITH a AS (SELECT order_id, customer_id, amount FROM dbo.orders WHERE status NOT IN ('cancelled','returned')),
b AS (SELECT customer_id, COUNT(*) AS n, SUM(amount) AS s FROM a GROUP BY customer_id),
c AS (SELECT customer_id, n, s, s / n AS avg_amt FROM b),
d AS (SELECT customer_id, n, s, avg_amt, CASE WHEN n >= 3 THEN 'frequent' WHEN n = 2 THEN 'repeat' ELSE 'one_off' END AS segment FROM c)
SELECT * INTO dbo.customer_segments_cte_chain FROM d;
""", r"""
with a as (select order_id, customer_id, amount from <<orders>> where lower(status) not in ('cancelled','returned')),
b as (select customer_id, count(*) as n, sum(amount) as s from a group by customer_id),
c as (select customer_id, n, s, s / n as avg_amt from b),
d as (select customer_id, n, s, avg_amt, case when n >= 3 then 'frequent' when n = 2 then 'repeat' else 'one_off' end as segment from c)
select * from d
"""),

("product_return_rate", "medium", ["float-division"], r"""
SELECT p.product_id, p.product_name, COUNT(*) AS line_count,
  SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS returned_lines,
  CAST(SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) AS return_rate
INTO dbo.product_return_rate FROM dbo.order_items i JOIN dbo.orders o ON o.order_id = i.order_id
JOIN dbo.products p ON p.product_id = i.product_id GROUP BY p.product_id, p.product_name;
""", r"""
select p.product_id, p.product_name, count(*) as line_count,
  sum(case when lower(o.status) = 'returned' then 1 else 0 end) as returned_lines,
  cast(sum(case when lower(o.status) = 'returned' then 1 else 0 end) as double) / count(*) as return_rate
from <<order_items>> i join <<orders>> o on o.order_id = i.order_id
join <<products>> p on p.product_id = i.product_id group by 1, 2
"""),

("east_markup_update_delete", "hard", ["update", "delete", "temp-tables", "decimal-rounding"], r"""
SELECT order_id, customer_id, amount, status INTO #o FROM dbo.orders;
UPDATE o SET amount = o.amount * 1.1 FROM #o o JOIN dbo.customers c ON c.customer_id = o.customer_id WHERE c.region = 'East';
DELETE FROM #o WHERE status = 'cancelled';
SELECT * INTO dbo.east_markup_update_delete FROM #o;
""", r"""
select o.order_id, o.customer_id,
  case when c.region = 'East' then round(o.amount * 1.1, 2) else o.amount end as amount, o.status
from <<orders>> o left join <<customers>> c on c.customer_id = o.customer_id
where lower(o.status) <> 'cancelled'
"""),

("customer_scorecard", "easy", ["conditional-aggregation"], r"""
SELECT c.customer_id,
  SUM(CASE WHEN o.status = 'shipped' THEN o.amount ELSE 0 END) AS shipped_amt,
  SUM(CASE WHEN o.status = 'pending' THEN o.amount ELSE 0 END) AS pending_amt,
  SUM(CASE WHEN o.status = 'cancelled' THEN o.amount ELSE 0 END) AS cancelled_amt,
  MAX(o.order_date) AS last_order, COUNT(o.order_id) AS orders
INTO dbo.customer_scorecard FROM dbo.customers c LEFT JOIN dbo.orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;
""", r"""
select c.customer_id,
  sum(case when lower(o.status) = 'shipped' then o.amount else 0 end) as shipped_amt,
  sum(case when lower(o.status) = 'pending' then o.amount else 0 end) as pending_amt,
  sum(case when lower(o.status) = 'cancelled' then o.amount else 0 end) as cancelled_amt,
  max(o.order_date) as last_order, count(o.order_id) as orders
from <<customers>> c left join <<orders>> o on o.customer_id = c.customer_id group by c.customer_id
"""),

("hardware_not_software_buyers", "easy", ["except"], r"""
SELECT DISTINCT o.customer_id INTO dbo.hardware_not_software_buyers FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id WHERE p.category = 'Hardware'
EXCEPT
SELECT DISTINCT o.customer_id FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id WHERE p.category = 'Software';
""", r"""
select distinct o.customer_id from <<orders>> o
join <<order_items>> i on i.order_id = o.order_id join <<products>> p on p.product_id = i.product_id where p.category = 'Hardware'
except
select distinct o.customer_id from <<orders>> o
join <<order_items>> i on i.order_id = o.order_id join <<products>> p on p.product_id = i.product_id where p.category = 'Software'
"""),

("rolling_30d_revenue", "hard", ["correlated-subquery", "date-window"], r"""
SELECT d.order_date,
  (SELECT SUM(o2.amount) FROM dbo.orders o2 WHERE o2.order_date > DATEADD(day, -30, d.order_date) AND o2.order_date <= d.order_date
     AND o2.status NOT IN ('cancelled','returned')) AS rolling_30d
INTO dbo.rolling_30d_revenue FROM (SELECT DISTINCT order_date FROM dbo.orders) d;
""", r"""
select d.order_date, sum(o2.amount) as rolling_30d
from (select distinct order_date from <<orders>>) d
left join <<orders>> o2 on o2.order_date > d.order_date - 30 and o2.order_date <= d.order_date
  and lower(o2.status) not in ('cancelled','returned')
group by d.order_date
"""),

("payment_balance_cursor", "hard", ["cursor", "running-total", "control-break"], r"""
CREATE TABLE dbo.payment_balance_cursor (payment_id INT, order_id INT, paid_amount DECIMAL(18,2), cumulative_paid DECIMAL(18,2), balance_after DECIMAL(18,2), overpaid INT);
DECLARE @pid INT, @oid INT, @paid DECIMAL(18,2), @amt DECIMAL(18,2), @prev INT = NULL, @cum DECIMAL(18,2) = 0;
DECLARE c CURSOR FOR SELECT p.payment_id, p.order_id, p.paid_amount, o.amount FROM dbo.payments p JOIN dbo.orders o ON o.order_id = p.order_id
  ORDER BY p.order_id, p.paid_date, p.payment_id;
OPEN c; FETCH NEXT FROM c INTO @pid, @oid, @paid, @amt;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @oid SET @cum = 0;
    SET @cum = @cum + @paid; SET @prev = @oid;
    INSERT INTO dbo.payment_balance_cursor VALUES (@pid, @oid, @paid, @cum, @amt - @cum, CASE WHEN @cum > @amt THEN 1 ELSE 0 END);
    FETCH NEXT FROM c INTO @pid, @oid, @paid, @amt;
END
CLOSE c; DEALLOCATE c;
""", r"""
select p.payment_id, p.order_id, p.paid_amount,
  sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) as cumulative_paid,
  o.amount - sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) as balance_after,
  case when sum(p.paid_amount) over (partition by p.order_id order by p.paid_date, p.payment_id rows between unbounded preceding and current row) > o.amount then 1 else 0 end as overpaid
from <<payments>> p join <<orders>> o on o.order_id = p.order_id
"""),

("region_isnull_truncation", "hard", ["isnull-type-truncation"], r"""
SELECT customer_id, ISNULL(region, 'Not_Assigned_Yet') AS region_isnull, COALESCE(region, 'Not_Assigned_Yet') AS region_coalesce
INTO dbo.region_isnull_truncation FROM dbo.customers;
""", r"""
select customer_id,
  coalesce(region, left('Not_Assigned_Yet', 10)) as region_isnull,
  coalesce(region, 'Not_Assigned_Yet') as region_coalesce
from <<customers>>
"""),

("customer_tags_split", "medium", ["string_split", "cross-apply"], r"""
SELECT c.customer_id, LTRIM(RTRIM(s.value)) AS tag INTO dbo.customer_tags_split FROM dbo.customers c
CROSS APPLY STRING_SPLIT(c.tags, ',') s WHERE c.tags IS NOT NULL;
""", r"""
select customer_id, trim(t) as tag from (
  select customer_id, unnest(string_split(tags, ',')) as t from <<customers>> where tags is not null) x
"""),

("dept_salary_rank", "medium", ["dense_rank", "window-sum", "decimal-cast"], r"""
SELECT employee_id, emp_name, department, salary,
  DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dept_rank,
  CAST(salary * 100.0 / SUM(salary) OVER (PARTITION BY department) AS DECIMAL(5,2)) AS pct_of_dept
INTO dbo.dept_salary_rank FROM dbo.employees;
""", r"""
select employee_id, emp_name, department, salary,
  dense_rank() over (partition by department order by salary desc) as dept_rank,
  cast(salary * 100.0 / sum(salary) over (partition by department) as decimal(5,2)) as pct_of_dept
from <<employees>>
"""),

("product_cross_sell", "medium", ["self-join"], r"""
SELECT a.product_id AS product_a, b.product_id AS product_b, COUNT(DISTINCT a.order_id) AS together
INTO dbo.product_cross_sell FROM dbo.order_items a JOIN dbo.order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
GROUP BY a.product_id, b.product_id;
""", r"""
select a.product_id as product_a, b.product_id as product_b, count(distinct a.order_id) as together
from <<order_items>> a join <<order_items>> b on a.order_id = b.order_id and a.product_id < b.product_id
group by 1, 2
"""),

# ---- the three that must go to a human -------------------------------------------------
("dynamic_sql_report", "human", ["dynamic-sql"], r"""
DECLARE @tbl SYSNAME, @col SYSNAME, @sql NVARCHAR(MAX);
SELECT TOP 1 @tbl = table_name, @col = filter_col FROM dbo.report_config;
SET @sql = N'SELECT * INTO dbo.dynamic_sql_report FROM dbo.' + QUOTENAME(@tbl) + N' WHERE ' + QUOTENAME(@col) + N' IS NOT NULL';
EXEC sp_executesql @sql;
""", None),

("random_audit_sample", "human", ["nondeterministic"], r"""
SELECT TOP 5 customer_id, customer_name, NEWID() AS audit_token, GETDATE() AS sampled_at
INTO dbo.random_audit_sample FROM dbo.customers ORDER BY NEWID();
""", None),

("archive_and_purge", "human", ["mutates-source"], r"""
SELECT * INTO dbo.archive_and_purge FROM dbo.orders WHERE status = 'cancelled' AND order_date < '2025-10-01';
DELETE FROM dbo.orders WHERE order_id IN (SELECT order_id FROM dbo.archive_and_purge);
UPDATE dbo.customers SET is_active = 0 WHERE customer_id NOT IN (SELECT customer_id FROM dbo.orders);
""", None),
]
