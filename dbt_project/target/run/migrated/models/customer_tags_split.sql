
  
  create view "warehouse"."main"."customer_tags_split__dbt_tmp" as (
    select customer_id, trim(t) as tag from (
  select customer_id, unnest(string_split(tags, ',')) as t from "warehouse"."legacy"."customers" where tags is not null) x
  );
