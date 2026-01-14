-- 1. Create Votes Table
create table if not exists comment_votes (
  user_id uuid references auth.users not null,
  comment_id bigint references comments not null, -- CHANGED to bigint
  vote_type int not null check (vote_type in (1, -1)), -- 1 for up, -1 for down
  created_at timestamptz default now(),
  primary key (user_id, comment_id)
);

-- 2. RLS
alter table comment_votes enable row level security;

-- DROP policies to ensure clean run
drop policy if exists "Users can vote" on comment_votes;
drop policy if exists "Users can change their vote" on comment_votes;
drop policy if exists "Users can remove their vote" on comment_votes;
drop policy if exists "Everyone can view votes" on comment_votes;

create policy "Users can vote"
  on comment_votes for insert
  with check (auth.uid() = user_id);

create policy "Users can change their vote"
  on comment_votes for update
  using (auth.uid() = user_id);

create policy "Users can remove their vote"
  on comment_votes for delete
  using (auth.uid() = user_id);

create policy "Everyone can view votes"
  on comment_votes for select
  using (true);

-- 3. RPC to fetch comments with vote counts & user status
drop function if exists get_comments_with_votes(uuid);
drop function if exists get_comments_with_votes(uuid, uuid);

create or replace function get_comments_with_votes(p_paper_id uuid, p_user_id uuid default null)
returns table (
  id bigint, -- CHANGED to bigint
  user_id uuid,
  paper_id uuid,
  content text,
  parent_id bigint, -- CHANGED to bigint (assuming parent_id is also bigint if it references id)
  created_at timestamptz,
  username text,
  full_name text,
  avatar_url text,
  score bigint,
  user_vote int
) as $$
begin
  return query
  select 
    c.id,
    c.user_id,
    c.paper_id,
    c.content,
    c.parent_id,
    c.created_at,
    p.username,
    p.full_name,
    p.avatar_url,
    coalesce(sum(v.vote_type), 0) as score,
    (select v2.vote_type from comment_votes v2 where v2.comment_id = c.id and v2.user_id = p_user_id) as user_vote
  from comments c
  left join profiles p on c.user_id = p.id
  left join comment_votes v on c.id = v.comment_id
  where c.paper_id = p_paper_id
  group by c.id, p.id, p.username, p.full_name, p.avatar_url
  order by c.created_at desc;
end;
$$ language plpgsql;
