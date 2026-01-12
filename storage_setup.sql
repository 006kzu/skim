values ('avatars', 'avatars', true)
on conflict (id) do nothing;

-- Ensure it is public (in case it existed as private)
update storage.buckets set public = true where id = 'avatars';

-- 2. Enable RLS skipped (usually already on)
-- alter table storage.objects enable row level security;

-- 3. Policy: Public Read Access (Anyone can view avatars)
drop policy if exists "Public Read Avatars" on storage.objects;
create policy "Public Read Avatars"
on storage.objects for select
using ( bucket_id = 'avatars' );

-- 4. Policy: Authenticated ALL (Allow insert/update/select/delete)
drop policy if exists "Authenticated Upload Avatars" on storage.objects;
drop policy if exists "Public Upload Avatars" on storage.objects; 
drop policy if exists "Owner Update Avatars" on storage.objects;
drop policy if exists "Authenticated ALL Avatars" on storage.objects;

create policy "Authenticated ALL Avatars"
on storage.objects for all
to authenticated
using ( bucket_id = 'avatars' )
with check ( bucket_id = 'avatars' );
