-- Enable RLS on saved_papers (safe to re-run)
alter table saved_papers enable row level security;

-- Policy to allow users to DELETE their own saved papers
drop policy if exists "Users can delete their own saved papers" on saved_papers;
create policy "Users can delete their own saved papers"
on saved_papers for delete
using (auth.uid() = user_id);

-- Policy to allow users to INSERT their own saved papers
drop policy if exists "Users can insert their own saved papers" on saved_papers;
create policy "Users can insert their own saved papers"
on saved_papers for insert
with check (auth.uid() = user_id);

-- Policy to allow users to SELECT their own saved papers
drop policy if exists "Users can view their own saved papers" on saved_papers;
create policy "Users can view their own saved papers"
on saved_papers for select
using (auth.uid() = user_id);

-- CRITICAL FIX: Policy to allow users to UPDATE their own saved papers (needed for last_viewed_at)
drop policy if exists "Users can update their own saved papers" on saved_papers;
create policy "Users can update their own saved papers"
on saved_papers for update
using (auth.uid() = user_id);
