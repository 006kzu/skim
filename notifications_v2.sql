-- 1. Ensure required columns exist
do $$
begin
  -- Check for last_viewed_at
  if not exists (select 1 from information_schema.columns 
                 where table_name = 'saved_papers' and column_name = 'last_viewed_at') then
    alter table saved_papers add column last_viewed_at timestamp with time zone default now();
  end if;

  -- Check for created_at (just in case it's missing or named differently, though it should be there)
  if not exists (select 1 from information_schema.columns 
                 where table_name = 'saved_papers' and column_name = 'created_at') then
    alter table saved_papers add column created_at timestamp with time zone default now();
  end if;
end $$;

-- 2. Create the RPC function to get saved papers with comment counts
-- Drop first to allow return type changes
drop function if exists get_favorites_with_counts(uuid);

create or replace function get_favorites_with_counts(current_user_id uuid)
returns table (
  id uuid,
  title text,
  summary text,
  url text, 
  score int,
  category text,
  authors text,
  date_added timestamptz,
  topic text,
  key_findings jsonb,
  implications jsonb,
  title_highlights jsonb,
  saved_at timestamptz,
  last_viewed_at timestamptz,
  new_comments_count bigint
) as $$
begin
  return query
  select 
    p.id,
    p.title,
    p.summary,
    p.url,
    p.score::int,
    p.category,
    p.authors,
    p.date_added,
    p.topic,
    p.key_findings,
    p.implications,
    p.title_highlights,
    sp.created_at as saved_at,
    sp.last_viewed_at,
    (
      select count(*)
      from comments c
      where c.paper_id = p.id
      and c.created_at > coalesce(sp.last_viewed_at, sp.created_at)
    ) as new_comments_count
  from saved_papers sp
  join papers p on sp.paper_id = p.id
  where sp.user_id = current_user_id
  order by sp.created_at desc;
end;
$$ language plpgsql;
