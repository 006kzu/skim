-- 1. Add Parent ID to Comments (Threading)
alter table comments 
add column parent_id bigint references comments(id) on delete cascade;

-- 2. Create Notifications Table
create table notifications (
  id bigint generated always as identity primary key,
  user_id uuid references public.profiles(id) on delete cascade not null, -- Who receives it
  actor_id uuid references public.profiles(id) on delete cascade,         -- Who triggered it
  resource_id bigint references comments(id) on delete cascade,           -- The comment involved
  is_read boolean default false,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. RLS Policies for Notifications
alter table notifications enable row level security;

-- View: Users can see their own notifications
create policy "Users can view own notifications"
on notifications for select
to authenticated
using (auth.uid() = user_id);

-- Update: Users can mark their own notifications as read
create policy "Users can update own notifications"
on notifications for update
to authenticated
using (auth.uid() = user_id);

-- Insert: Users can create notifications for OTHERS (e.g. when replying)
create policy "Users can insert notifications"
on notifications for insert
to authenticated
with check (true);
