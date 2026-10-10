select customer_id, trim(t) as tag from (
  select customer_id, unnest(string_split(tags, ',')) as t from "warehouse"."legacy"."customers" where tags is not null) x