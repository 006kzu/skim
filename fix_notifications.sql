-- Function to create notification securely (bypassing RLS via security definer)
create or replace function create_notification_safe(
  recipient_id uuid,
  sender_id uuid,
  comment_id bigint
)
returns void
language plpgsql
security definer -- This makes it run with the privileges of the creator (admin), bypassing RLS
as $$
begin
  insert into notifications (user_id, actor_id, resource_id)
  values (recipient_id, sender_id, comment_id);
end;
$$;
