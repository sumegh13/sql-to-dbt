SELECT DISTINCT
  customer_id,
  FIRST_VALUE(order_id) OVER (
    PARTITION BY customer_id
    ORDER BY order_date ASC NULLS FIRST, order_id ASC NULLS FIRST
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) AS first_order,
  LAST_VALUE(order_id) OVER (
    PARTITION BY customer_id
    ORDER BY order_date ASC NULLS FIRST, order_id ASC NULLS FIRST
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
  ) AS last_order
FROM "warehouse"."legacy"."orders"