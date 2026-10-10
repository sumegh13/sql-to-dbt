select product_id, price, effective_date from (
  select product_id, price, effective_date,
         row_number() over (partition by product_id order by effective_date desc) as rn
  from {{ source('legacy', 'price_history') }} where effective_date <= date '2025-12-31') r
where rn = 1
