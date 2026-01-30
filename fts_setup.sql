-- Enable the pg_trgm extension for fuzzy matching (optional but good for future)
create extension if not exists pg_trgm;

-- Add generated column for Full Text Search
-- This combines title, summary, and category into a single searchable vector
alter table papers 
add column if not exists fts tsvector 
generated always as (
  to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(category, ''))
) stored;

-- Create GIN index for fast searching
create index if not exists papers_fts_idx on papers using gin (fts);

-- Function to search papers using FTS
-- This allows us to use RPC call if needed, or we can use the client.rpc or .text_search()
create or replace function search_papers_fts(query_text text)
returns setof papers as $$
begin
  return query
  select *
  from papers
  where fts @@ plainto_tsquery('english', query_text)
  order by ts_rank(fts, plainto_tsquery('english', query_text)) desc;
end;
$$ language plpgsql stable;
