WITH src AS (
    SELECT
        email,
        strpos(email, '@') AS at_pos
    FROM "warehouse"."legacy"."customers"
    WHERE email IS NOT NULL
),
parts AS (
    SELECT
        SUBSTRING(email, at_pos + 1, length(rtrim(email))) AS domain
    FROM src
)
SELECT
    min(domain) AS domain,
    count(*) AS customers
FROM parts
GROUP BY rtrim(lower(domain))