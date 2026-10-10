WITH priced AS (
    SELECT
        product_id,
        price,
        effective_date,
        LEAD(effective_date) OVER (PARTITION BY product_id ORDER BY effective_date) AS next_effective_date
    FROM "warehouse"."legacy"."price_history"
)
SELECT
    product_id,
    price,
    effective_date AS valid_from,
    COALESCE(next_effective_date, DATE '9999-12-31') AS valid_to,
    CASE WHEN next_effective_date IS NULL THEN 1 ELSE 0 END AS is_current
FROM priced