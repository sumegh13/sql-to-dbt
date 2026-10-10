SELECT
    p.product_id,
    p.product_name,
    SUM(inv.qty_on_hand) AS total_qty,
    CASE WHEN SUM(inv.qty_on_hand) < 20 THEN 1 ELSE 0 END AS low_stock
FROM "warehouse"."legacy"."products" AS p
LEFT JOIN "warehouse"."legacy"."inventory" AS inv
    ON inv.product_id = p.product_id
GROUP BY p.product_id, p.product_name