"""Proc specs 001-025. Each: (slug, difficulty, tags, T-SQL body, reference dbt model).
Body runs inside the generated proc; it must create dbo.<slug>. Models use <<table>> for sources."""

NOT_CANCELLED = "status NOT IN ('cancelled','returned')"

SPECS_A = [
("customer_order_totals", "medium", ["cursor"], r"""
CREATE TABLE dbo.customer_order_totals (customer_id INT, customer_name VARCHAR(100), order_count INT, total_amount DECIMAL(18,2), tier VARCHAR(10));
DECLARE @id INT, @name VARCHAR(100), @cnt INT, @amt DECIMAL(18,2);
DECLARE c CURSOR FOR SELECT customer_id, customer_name FROM dbo.customers;
OPEN c; FETCH NEXT FROM c INTO @id, @name;
WHILE @@FETCH_STATUS = 0
BEGIN
    SELECT @cnt = COUNT(*), @amt = ISNULL(SUM(amount),0) FROM dbo.orders WHERE customer_id=@id AND status<>'cancelled';
    INSERT INTO dbo.customer_order_totals VALUES (@id,@name,@cnt,@amt,
        CASE WHEN @amt>=1000 THEN 'gold' WHEN @amt>=500 THEN 'silver' ELSE 'bronze' END);
    FETCH NEXT FROM c INTO @id, @name;
END
CLOSE c; DEALLOCATE c;
""", r"""
select c.customer_id, c.customer_name, count(o.order_id) as order_count,
       coalesce(sum(o.amount), 0) as total_amount,
       case when coalesce(sum(o.amount), 0) >= 1000 then 'gold'
            when coalesce(sum(o.amount), 0) >= 500 then 'silver' else 'bronze' end as tier
from <<customers>> c
left join <<orders>> o on o.customer_id = c.customer_id and lower(o.status) <> 'cancelled'
group by c.customer_id, c.customer_name
"""),

("active_customers_by_region", "easy", ["isnull", "group-by"], r"""
SELECT ISNULL(region,'Unknown') AS region, COUNT(*) AS customer_count INTO dbo.active_customers_by_region
FROM dbo.customers WHERE is_active = 1 GROUP BY ISNULL(region,'Unknown');
""", r"""
select coalesce(region, 'Unknown') as region, count(*) as customer_count
from <<customers>> where is_active = 1 group by 1
"""),

("monthly_revenue", "easy", ["case-insensitive-collation", "datepart"], r"""
SELECT YEAR(order_date) AS yr, MONTH(order_date) AS mo, SUM(amount) AS revenue INTO dbo.monthly_revenue
FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY YEAR(order_date), MONTH(order_date);
""", r"""
select year(order_date) as yr, month(order_date) as mo, sum(amount) as revenue
from <<orders>> where lower(status) not in ('cancelled','returned') group by 1, 2
"""),

("top_products_by_revenue", "easy", ["top-n"], r"""
SELECT TOP 5 p.product_id, p.product_name, SUM(i.qty * i.unit_price) AS revenue INTO dbo.top_products_by_revenue
FROM dbo.order_items i JOIN dbo.products p ON p.product_id = i.product_id
GROUP BY p.product_id, p.product_name ORDER BY SUM(i.qty * i.unit_price) DESC, p.product_id;
""", r"""
select p.product_id, p.product_name, sum(i.qty * i.unit_price) as revenue
from <<order_items>> i join <<products>> p on p.product_id = i.product_id
group by 1, 2 order by revenue desc, p.product_id limit 5
"""),

("customer_email_domains", "easy", ["string-functions"], r"""
SELECT SUBSTRING(email, CHARINDEX('@',email)+1, LEN(email)) AS domain, COUNT(*) AS customers INTO dbo.customer_email_domains
FROM dbo.customers WHERE email IS NOT NULL GROUP BY SUBSTRING(email, CHARINDEX('@',email)+1, LEN(email));
""", r"""
select split_part(email, '@', 2) as domain, count(*) as customers
from <<customers>> where email is not null group by 1
"""),

("order_age_buckets", "easy", ["datediff"], r"""
SELECT order_id, DATEDIFF(day, order_date, '2025-12-31') AS age_days,
  CASE WHEN DATEDIFF(day, order_date, '2025-12-31') <= 30 THEN '0-30'
       WHEN DATEDIFF(day, order_date, '2025-12-31') <= 90 THEN '31-90' ELSE '90+' END AS bucket
INTO dbo.order_age_buckets FROM dbo.orders;
""", r"""
select order_id, date_diff('day', order_date, date '2025-12-31') as age_days,
  case when date_diff('day', order_date, date '2025-12-31') <= 30 then '0-30'
       when date_diff('day', order_date, date '2025-12-31') <= 90 then '31-90' else '90+' end as bucket
from <<orders>>
"""),

("payment_status", "easy", ["left-join"], r"""
SELECT o.order_id, o.amount, ISNULL(SUM(p.paid_amount),0) AS paid,
  CASE WHEN ISNULL(SUM(p.paid_amount),0) >= o.amount THEN 'paid'
       WHEN ISNULL(SUM(p.paid_amount),0) > 0 THEN 'partial' ELSE 'unpaid' END AS payment_status
INTO dbo.payment_status FROM dbo.orders o LEFT JOIN dbo.payments p ON p.order_id = o.order_id
GROUP BY o.order_id, o.amount;
""", r"""
select o.order_id, o.amount, coalesce(sum(p.paid_amount), 0) as paid,
  case when coalesce(sum(p.paid_amount), 0) >= o.amount then 'paid'
       when coalesce(sum(p.paid_amount), 0) > 0 then 'partial' else 'unpaid' end as payment_status
from <<orders>> o left join <<payments>> p on p.order_id = o.order_id
group by o.order_id, o.amount
"""),

("avg_item_by_category", "medium", ["decimal-avg"], r"""
SELECT p.category, AVG(i.qty * i.unit_price) AS avg_line_value, COUNT(*) AS line_count INTO dbo.avg_item_by_category
FROM dbo.order_items i JOIN dbo.products p ON p.product_id = i.product_id GROUP BY p.category;
""", r"""
select p.category, avg(i.qty * i.unit_price) as avg_line_value, count(*) as line_count
from <<order_items>> i join <<products>> p on p.product_id = i.product_id group by 1
"""),

("cancel_pct_int_division", "medium", ["integer-division"], r"""
SELECT customer_id, COUNT(*) AS total_orders,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) * 100 / COUNT(*) AS cancel_pct
INTO dbo.cancel_pct_int_division FROM dbo.orders GROUP BY customer_id;
""", r"""
select customer_id, count(*) as total_orders,
  sum(case when lower(status) = 'cancelled' then 1 else 0 end) as cancelled_orders,
  sum(case when lower(status) = 'cancelled' then 1 else 0 end) * 100 // count(*) as cancel_pct
from <<orders>> group by customer_id
"""),

("customers_without_orders", "easy", ["not-exists"], r"""
SELECT c.customer_id, c.customer_name INTO dbo.customers_without_orders FROM dbo.customers c
WHERE NOT EXISTS (SELECT 1 FROM dbo.orders o WHERE o.customer_id = c.customer_id);
""", r"""
select c.customer_id, c.customer_name from <<customers>> c
where not exists (select 1 from <<orders>> o where o.customer_id = c.customer_id)
"""),

("employee_salary_bands", "easy", ["iif"], r"""
SELECT employee_id, emp_name, salary, IIF(salary >= 120000, 'senior', IIF(salary >= 70000, 'mid', 'junior')) AS band
INTO dbo.employee_salary_bands FROM dbo.employees;
""", r"""
select employee_id, emp_name, salary,
  case when salary >= 120000 then 'senior' when salary >= 70000 then 'mid' else 'junior' end as band
from <<employees>>
"""),

("inventory_low_stock", "easy", ["left-join", "iif"], r"""
SELECT p.product_id, p.product_name, SUM(inv.qty_on_hand) AS total_qty,
  IIF(SUM(inv.qty_on_hand) < 20, 1, 0) AS low_stock
INTO dbo.inventory_low_stock FROM dbo.products p LEFT JOIN dbo.inventory inv ON inv.product_id = p.product_id
GROUP BY p.product_id, p.product_name;
""", r"""
select p.product_id, p.product_name, sum(inv.qty_on_hand) as total_qty,
  case when sum(inv.qty_on_hand) < 20 then 1 else 0 end as low_stock
from <<products>> p left join <<inventory>> inv on inv.product_id = p.product_id
group by 1, 2
"""),

("order_product_list", "medium", ["string_agg"], r"""
SELECT o.order_id, STRING_AGG(p.product_name, ', ') WITHIN GROUP (ORDER BY p.product_name) AS products
INTO dbo.order_product_list FROM dbo.orders o
JOIN dbo.order_items i ON i.order_id = o.order_id JOIN dbo.products p ON p.product_id = i.product_id
GROUP BY o.order_id;
""", r"""
select o.order_id, string_agg(p.product_name, ', ' order by p.product_name) as products
from <<orders>> o join <<order_items>> i on i.order_id = o.order_id
join <<products>> p on p.product_id = i.product_id group by o.order_id
"""),

("buyers_by_region", "easy", ["count-distinct", "null-group"], r"""
SELECT c.region, COUNT(DISTINCT c.customer_id) AS buyers INTO dbo.buyers_by_region
FROM dbo.customers c JOIN dbo.orders o ON o.customer_id = c.customer_id GROUP BY c.region;
""", r"""
select c.region, count(distinct c.customer_id) as buyers
from <<customers>> c join <<orders>> o on o.customer_id = c.customer_id group by c.region
"""),

("latest_product_price", "medium", ["row_number", "cte"], r"""
WITH r AS (
  SELECT product_id, price, effective_date, ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_date DESC) AS rn
  FROM dbo.price_history WHERE effective_date <= '2025-12-31')
SELECT product_id, price, effective_date INTO dbo.latest_product_price FROM r WHERE rn = 1;
""", r"""
select product_id, price, effective_date from (
  select product_id, price, effective_date,
         row_number() over (partition by product_id order by effective_date desc) as rn
  from <<price_history>> where effective_date <= date '2025-12-31') r
where rn = 1
"""),

("running_total_cursor", "hard", ["cursor", "running-total"], r"""
CREATE TABLE dbo.running_total_cursor (customer_id INT, order_id INT, order_date DATE, amount DECIMAL(18,2), running_total DECIMAL(18,2));
DECLARE @cust INT, @oid INT, @dt DATE, @amt DECIMAL(18,2), @prev INT = NULL, @run DECIMAL(18,2) = 0;
DECLARE c CURSOR FOR SELECT customer_id, order_id, order_date, amount FROM dbo.orders ORDER BY customer_id, order_date, order_id;
OPEN c; FETCH NEXT FROM c INTO @cust, @oid, @dt, @amt;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF @prev IS NULL OR @prev <> @cust SET @run = 0;
    SET @run = @run + @amt; SET @prev = @cust;
    INSERT INTO dbo.running_total_cursor VALUES (@cust, @oid, @dt, @amt, @run);
    FETCH NEXT FROM c INTO @cust, @oid, @dt, @amt;
END
CLOSE c; DEALLOCATE c;
""", r"""
select customer_id, order_id, order_date, amount,
  sum(amount) over (partition by customer_id order by order_date, order_id rows between unbounded preceding and current row) as running_total
from <<orders>>
"""),

("order_rank_per_customer", "medium", ["window-ranking"], r"""
SELECT order_id, customer_id, amount,
  ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC, order_id) AS rn,
  RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rnk,
  DENSE_RANK() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS drnk
INTO dbo.order_rank_per_customer FROM dbo.orders;
""", r"""
select order_id, customer_id, amount,
  row_number() over (partition by customer_id order by amount desc, order_id) as rn,
  rank() over (partition by customer_id order by amount desc) as rnk,
  dense_rank() over (partition by customer_id order by amount desc) as drnk
from <<orders>>
"""),

("temp_table_pipeline", "medium", ["temp-tables"], r"""
SELECT customer_id, SUM(amount) AS spend INTO #spend FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY customer_id;
SELECT c.customer_id, c.customer_name, ISNULL(s.spend, 0) AS spend INTO #joined FROM dbo.customers c LEFT JOIN #spend s ON s.customer_id = c.customer_id;
SELECT j.customer_id, j.customer_name, j.spend,
  CASE WHEN j.spend > (SELECT AVG(spend) FROM #joined) THEN 'above_avg' ELSE 'at_or_below_avg' END AS vs_avg
INTO dbo.temp_table_pipeline FROM #joined j;
""", r"""
with spend as (
  select customer_id, sum(amount) as spend from <<orders>>
  where lower(status) not in ('cancelled','returned') group by customer_id),
joined as (
  select c.customer_id, c.customer_name, coalesce(s.spend, 0) as spend
  from <<customers>> c left join spend s on s.customer_id = c.customer_id)
select j.customer_id, j.customer_name, j.spend,
  case when j.spend > (select avg(spend) from joined) then 'above_avg' else 'at_or_below_avg' end as vs_avg
from joined j
"""),

("customer_spend_quartiles", "medium", ["ntile", "cte"], r"""
WITH s AS (SELECT customer_id, SUM(amount) AS spend FROM dbo.orders WHERE status NOT IN ('cancelled','returned') GROUP BY customer_id)
SELECT customer_id, spend, NTILE(4) OVER (ORDER BY spend DESC, customer_id) AS quartile
INTO dbo.customer_spend_quartiles FROM s;
""", r"""
with s as (select customer_id, sum(amount) as spend from <<orders>>
           where lower(status) not in ('cancelled','returned') group by customer_id)
select customer_id, spend, ntile(4) over (order by spend desc, customer_id) as quartile from s
"""),

("merge_customer_dim", "hard", ["merge", "upsert"], r"""
SELECT customer_id, customer_name, region, email INTO #tgt FROM dbo.customers;
MERGE #tgt AS t USING dbo.customer_staging AS s ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET customer_name = s.customer_name, region = s.region, email = ISNULL(s.email, t.email)
WHEN NOT MATCHED BY TARGET THEN INSERT (customer_id, customer_name, region, email) VALUES (s.customer_id, s.customer_name, s.region, s.email);
SELECT * INTO dbo.merge_customer_dim FROM #tgt;
""", r"""
select coalesce(s.customer_id, t.customer_id) as customer_id,
  case when s.customer_id is not null then s.customer_name else t.customer_name end as customer_name,
  case when s.customer_id is not null then s.region else t.region end as region,
  coalesce(s.email, t.email) as email
from <<customers>> t full outer join <<customer_staging>> s on t.customer_id = s.customer_id
"""),

("price_scd2", "hard", ["scd2", "lead"], r"""
SELECT product_id, price, effective_date AS valid_from,
  ISNULL(LEAD(effective_date) OVER (PARTITION BY product_id ORDER BY effective_date), '9999-12-31') AS valid_to,
  CASE WHEN LEAD(effective_date) OVER (PARTITION BY product_id ORDER BY effective_date) IS NULL THEN 1 ELSE 0 END AS is_current
INTO dbo.price_scd2 FROM dbo.price_history;
""", r"""
select product_id, price, effective_date as valid_from,
  coalesce(lead(effective_date) over (partition by product_id order by effective_date), date '9999-12-31') as valid_to,
  case when lead(effective_date) over (partition by product_id order by effective_date) is null then 1 else 0 end as is_current
from <<price_history>>
"""),

("order_streaks", "hard", ["gaps-and-islands"], r"""
WITH d AS (SELECT DISTINCT customer_id, order_date FROM dbo.orders),
g AS (SELECT customer_id, order_date,
        DATEADD(day, -ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date), order_date) AS grp FROM d)
SELECT customer_id, MIN(order_date) AS streak_start, MAX(order_date) AS streak_end, COUNT(*) AS days
INTO dbo.order_streaks FROM g GROUP BY customer_id, grp;
""", r"""
with d as (select distinct customer_id, order_date from <<orders>>),
g as (select customer_id, order_date,
        order_date - cast(row_number() over (partition by customer_id order by order_date) as integer) as grp from d)
select customer_id, min(order_date) as streak_start, max(order_date) as streak_end, count(*) as days
from g group by customer_id, grp
"""),

("org_hierarchy", "hard", ["recursive-cte"], r"""
WITH h AS (
  SELECT employee_id, emp_name, manager_id, 0 AS lvl, CAST(emp_name AS VARCHAR(500)) AS path
  FROM dbo.employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.employee_id, e.emp_name, e.manager_id, h.lvl + 1, CAST(h.path + ' > ' + e.emp_name AS VARCHAR(500))
  FROM dbo.employees e JOIN h ON e.manager_id = h.employee_id)
SELECT employee_id, emp_name, lvl, path INTO dbo.org_hierarchy FROM h;
""", r"""
with recursive h as (
  select employee_id, emp_name, manager_id, 0 as lvl, cast(emp_name as varchar) as path
  from <<employees>> where manager_id is null
  union all
  select e.employee_id, e.emp_name, e.manager_id, h.lvl + 1, h.path || ' > ' || e.emp_name
  from <<employees>> e join h on e.manager_id = h.employee_id)
select employee_id, emp_name, lvl, path from h
"""),

("daily_calendar_loop", "medium", ["while-loop", "calendar"], r"""
CREATE TABLE dbo.daily_calendar_loop (cal_date DATE, orders_placed INT);
DECLARE @d DATE = '2025-11-01';
WHILE @d <= '2025-12-31'
BEGIN
    INSERT INTO dbo.daily_calendar_loop SELECT @d, COUNT(*) FROM dbo.orders WHERE order_date = @d;
    SET @d = DATEADD(day, 1, @d);
END
""", r"""
select cast(d.d as date) as cal_date, count(o.order_id) as orders_placed
from generate_series(date '2025-11-01', date '2025-12-31', interval 1 day) as d(d)
left join <<orders>> o on o.order_date = cast(d.d as date)
group by 1
"""),

("status_pivot", "medium", ["pivot", "case-insensitive-collation"], r"""
SELECT customer_id, ISNULL([shipped],0) AS shipped, ISNULL([pending],0) AS pending, ISNULL([cancelled],0) AS cancelled
INTO dbo.status_pivot FROM (SELECT customer_id, status, order_id FROM dbo.orders) src
PIVOT (COUNT(order_id) FOR status IN ([shipped],[pending],[cancelled])) p;
""", r"""
select customer_id,
  count(*) filter (where lower(status) = 'shipped') as shipped,
  count(*) filter (where lower(status) = 'pending') as pending,
  count(*) filter (where lower(status) = 'cancelled') as cancelled
from <<orders>> group by customer_id
"""),
]
