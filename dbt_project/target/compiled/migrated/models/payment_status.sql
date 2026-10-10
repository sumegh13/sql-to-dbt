SELECT
    o.order_id,
    o.amount,
    COALESCE(SUM(p.paid_amount), 0) AS paid,
    CASE
        WHEN COALESCE(SUM(p.paid_amount), 0) >= o.amount THEN 'paid'
        WHEN COALESCE(SUM(p.paid_amount), 0) > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS payment_status
FROM "warehouse"."legacy"."orders" o
LEFT JOIN "warehouse"."legacy"."payments" p
    ON p.order_id = o.order_id
GROUP BY o.order_id, o.amount