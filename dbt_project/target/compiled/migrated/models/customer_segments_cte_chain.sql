WITH a AS (
    SELECT
        customer_id,
        amount
    FROM "warehouse"."legacy"."orders"
    WHERE rtrim(lower(status)) NOT IN ('cancelled', 'returned')
),
b AS (
    SELECT
        customer_id,
        COUNT(*) AS n,
        SUM(amount) AS s
    FROM a
    GROUP BY customer_id
),
c AS (
    SELECT
        customer_id,
        n,
        s,
        CAST(s AS DOUBLE) / n AS avg_amt
    FROM b
),
d AS (
    SELECT
        customer_id,
        n,
        s,
        avg_amt,
        CASE
            WHEN n >= 3 THEN 'frequent'
            WHEN n = 2 THEN 'repeat'
            ELSE 'one_off'
        END AS segment
    FROM c
)
SELECT
    customer_id,
    n,
    s,
    avg_amt,
    segment
FROM d