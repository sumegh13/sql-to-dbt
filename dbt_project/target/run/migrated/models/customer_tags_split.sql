
  
  create view "warehouse"."main"."customer_tags_split__dbt_tmp" as (
    with split_tags as (
    select
        c.customer_id,
        unnest(string_split(c.tags, ',')) as raw_tag
    from "warehouse"."legacy"."customers" as c
    where c.tags is not null
)
select
    customer_id,
    rtrim(ltrim(raw_tag)) as tag
from split_tags
  );
