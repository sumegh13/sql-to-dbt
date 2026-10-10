WITH parsed AS (
    SELECT
        substr(
            email,
            instr(email, '@') + 1,
            length(rtrim(email))
        ) AS domain
    FROM "warehouse"."legacy"."customers"
    WHERE email IS NOT NULL
)
SELECT
    min(domain) AS domain,
    count(*) AS customers
FROM parsed
GROUP BY rtrim(lower(domain))