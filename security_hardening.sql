-- ==========================================
-- Security Hardening Script
-- ==========================================

-- 1. Hardening 'papers' Table
-- ------------------------------------------
ALTER TABLE papers ENABLE ROW LEVEL SECURITY;

-- Allow public read access (SELECT)
DROP POLICY IF EXISTS "Public can view papers" ON papers;
CREATE POLICY "Public can view papers"
  ON papers FOR SELECT
  USING ( true );

-- Restrict modifications (INSERT, UPDATE, DELETE) to Service Role only.
-- The "anon" or "authenticated" roles will be denied by default since no policy grants them write access.
-- Using the Service Role key (backend scripts) bypasses RLS automatically.


-- 2. Hardening 'notifications' Table
-- ------------------------------------------
-- Fix loose INSERT policy that allowed spoofing sender_id
DROP POLICY IF EXISTS "Users can insert notifications" ON notifications;

CREATE POLICY "Users can insert notifications (Strict)"
  ON notifications FOR INSERT
  TO authenticated
  WITH CHECK (
    -- User can only insert if they are the sender
    auth.uid() = actor_id
    -- OR if you strictly follow the logic that sender_id MUST be auth.uid()
  );


-- 3. Hardening 'storage.objects' (Avatars)
-- ------------------------------------------
-- Remove the overly permissive policies
DROP POLICY IF EXISTS "Authenticated ALL Avatars" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated Upload Avatars" ON storage.objects;
DROP POLICY IF EXISTS "Public Upload Avatars" ON storage.objects;

-- Allow Users to Manage THEIR OWN Avatars Only
-- This requires the file path to follow the pattern: {user_id}/filename
CREATE POLICY "Users manage own avatars"
  ON storage.objects FOR ALL
  TO authenticated
  USING (
    bucket_id = 'avatars' 
    AND (storage.foldername(name))[1] = auth.uid()::text
  )
  WITH CHECK (
    bucket_id = 'avatars' 
    AND (storage.foldername(name))[1] = auth.uid()::text
  );

-- Keep Public Read
-- (Assuming 'Public Read Avatars' policy exists from storage_setup.sql, if not ensure it:)
DROP POLICY IF EXISTS "Public Read Avatars" ON storage.objects;
CREATE POLICY "Public Read Avatars"
  ON storage.objects FOR SELECT
  USING ( bucket_id = 'avatars' );
