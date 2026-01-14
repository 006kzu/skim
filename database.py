import os
from supabase import create_client, Client, ClientOptions
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv(override=True)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Initialize Client
if url and key:
    # Fix for 'Storage endpoint URL should have a trailing slash'
    if not url.endswith("/"):
        url += "/"
    print(f"DEBUG: Connecting to Supabase Project: {url}")
    supabase: Client = create_client(url, key)
else:
    supabase = None
    print("⚠️ WARNING: Supabase keys not found. Database features will fail.")


def init_db():
    """
    Legacy compatibility. 
    Supabase tables are created via the web dashboard SQL editor.
    """
    pass


def save_paper(paper, search_topic):
    """Saves a paper to Supabase Cloud."""
    if not supabase:
        print("❌ DB Error: No connection.")
        return

    # 1. PREPARE THE DATA
    data = paper.copy()

    # 2. ADD TOPIC
    data['topic'] = search_topic

    # 3. SAFETY CHECKS
    # The API returns 'url', but sometimes your code might look for 'link'
    if 'link' in data and 'url' not in data:
        data['url'] = data.pop('link')  # Rename link -> url

    # Ensure 'url' isn't None
    if not data.get('url'):
        if data.get('paperId'):
            data['url'] = f"https://www.semanticscholar.org/paper/{data['paperId']}"
        else:
            data['url'] = ""

    # Ensure 'title_highlights' exists (defaults to empty list)
    if 'title_highlights' not in data:
        data['title_highlights'] = []

    # 4. REMOVE ID (Critical Fix)
    # We MUST delete the 'id' field so Supabase generates a new UUID.
    if 'id' in data:
        del data['id']

    # 5. INSERT
    try:
        response = supabase.table("papers").insert(data).execute()
        print(f"   ✅ DB Saved: {data['title'][:30]}...")
        if response.data and len(response.data) > 0:
            return response.data[0]['id']
    except Exception as e:
        # Ignore duplicate errors, print others
        if "duplicate key" in str(e):
            print(f"   ⚠️ Skipped (Already in DB): {data['title'][:20]}...")
            # Try to fetch existing ID if duplicate
            # This is a bit expensive but necessary if we want to favorite it immediately
            try:
                # Assuming uniqueness by URL or Title?
                # The schema doesn't strictly enforce unique title/url unless added
                # But let's assume we can try to find it.
                # Actually, simply returning None implies "Already Exists" 
                # but we need the ID.
                pass 
            except:
                pass
        else:
            print(f"   ☁️ Cloud DB Error: {e}")
    return None


def get_papers_by_topic(topic, limit=20):
    """Fetches papers for a specific topic."""
    if not supabase:
        return []

    try:
        response = supabase.table("papers") \
            .select("*") \
            .eq("topic", topic) \
            .order("date_added", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching topic: {e}")
        return []


def get_top_rated_papers(limit=8):
    """Fetches the global top hits (Score >= 7)."""
    if not supabase:
        return []

    try:
        response = supabase.table("papers") \
            .select("*") \
            .gte("score", 7) \
            .order("score", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching top hits: {e}")
        return []


# --- NEW FUNCTIONS ADDED FOR REPAIR SCRIPT ---

def get_all_papers_raw():
    """Fetches all papers to check for missing fields."""
    if not supabase:
        print("❌ Error: Supabase client is not initialized.")
        return []
    try:
        # Select all columns
        response = supabase.table("papers").select("*").execute()
        return response.data
    except Exception as e:
        print(f"❌ Error fetching all papers: {e}")
        return []


def update_paper(paper_id, update_data):
    """Updates a specific paper record by its unique ID."""
    if not supabase:
        return
    try:
        response = supabase.table("papers").update(
            update_data).eq("id", paper_id).execute()

        # 🚨 CHECK: Did we actually update anything?
        if len(response.data) > 0:
            print(
                f"   ✅ DB Updated: {update_data.get('title', 'Paper')[:20]}...")
        else:
            print(f"   ⚠️ UPDATE IGNORED (0 rows): Check your .env permissions (RLS)!")

    except Exception as e:
        print(f"   ❌ Update Failed for ID {paper_id}: {e}")

# --- USER & PROFILE FUNCTIONS ---

def get_profile(user_id):
    """Fetches user profile by ID."""
    if not supabase:
        return None
    try:
        # manual single check using limit(1) to avoid compat issues
        res = supabase.table("profiles").select("*").eq("id", user_id).limit(1).execute()
        if res and res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

def create_profile(user_id, metadata, email=None):
    """Creates a new profile if one doesn't exist."""
    if not supabase:
        return None
    try:
        # metadata is the 'user_metadata' from auth
        full_name = metadata.get('full_name') or metadata.get('name')
        avatar_url = metadata.get('avatar_url') or metadata.get('picture')
        username = metadata.get('username')
        
        data = {
            "id": user_id,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "username": username,
            "email": email,
            "updated_at": "now()"
        }
        res = supabase.table("profiles").insert(data).execute()
        if res:
             return res.data
        return None
    except Exception as e:
        print(f"Error creating profile: {e}")
        return None

def update_profile(user_id, updates):
    """Updates user profile."""
    if not supabase:
        return None
    try:
        res = supabase.table("profiles").update(updates).eq("id", user_id).execute()
        return res.data
    except Exception as e:
        print(f"Error updating profile: {e}")
        return None

def upload_avatar(user_id, file_obj, file_ext, access_token=None):
    """Uploads avatar using authenticated client."""
    if not supabase:
        return None
    try:
        path = f"{user_id}/avatar.{file_ext}"
        bucket = "avatars"
        
        # Use a scoped client if token provided (Secure Upload)
        client_to_use = supabase
        if access_token:
            # Fix URL again locally just in case
            safe_url = url
            if not safe_url.endswith("/"):
                safe_url += "/"
                
            # Create a lightweight client copy with auth headers
            opts = ClientOptions(headers={"Authorization": f"Bearer {access_token}"})
            client_to_use = create_client(safe_url, key, options=opts)

        # 1. Upload
        res = client_to_use.storage.from_(bucket).upload(path, file_obj, {"upsert": "true", "content-type": f"image/{file_ext}"})
        
        # 2. Get Public URL
        public_url = supabase.storage.from_(bucket).get_public_url(path)
        
        # Add cache buster
        import time
        final_url = f"{public_url}?t={int(time.time())}"

        # 3. Update Profile
        if access_token:
             # Use scoped client for update too
             client_to_use.table("profiles").update({"avatar_url": final_url}).eq("id", user_id).execute()
        else:
             update_profile(user_id, {"avatar_url": final_url})
        
        return final_url
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        return None

# --- SAVED PAPERS (FAVORITES) ---

def save_favorite(user_id, paper_id):
    """Saves a paper to the user's library."""
    if not supabase:
        return False
    try:
        supabase.table("saved_papers").insert({
            "user_id": user_id,
            "paper_id": paper_id
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving favorite: {e}")
        return False

def remove_favorite(user_id, paper_id):
    """Removes a paper from the user's library."""
    if not supabase:
        return False
    try:
        supabase.table("saved_papers").delete().eq("user_id", user_id).eq("paper_id", paper_id).execute()
        return True
    except Exception as e:
        print(f"Error removing favorite: {e}")
        return False

def get_favorites(user_id):
    """Fetches all saved papers for a user, including new comment counts."""
    if not supabase:
        return []
    try:
        # Use the RPC function to get paper details + unread comment counts efficiently
        # This replaces the join query
        res = supabase.rpc("get_favorites_with_counts", {"current_user_id": user_id}).execute()
        
        papers = []
        for p in res.data:
            # Add flag
            p['_is_saved'] = True
            # Ensure proper type for new_comments_count
            p['new_comments_count'] = p.get('new_comments_count', 0)
            papers.append(p)
        return papers
    except Exception as e:
        print(f"Error fetching favorites: {e}")
        # Fallback to old method if RPC fails
        try:
             res = supabase.table("saved_papers").select("*, papers(*)").eq("user_id", user_id).execute()
             papers = []
             for item in res.data:
                 if item.get('papers'):
                     p = item['papers']
                     p['_is_saved'] = True
                     papers.append(p)
             return papers
        except:
            return []

def mark_paper_viewed(user_id, paper_id):
    """Updates the last_viewed_at timestamp for a saved paper."""
    if not supabase:
        return
    try:
        supabase.table("saved_papers").update({
            "last_viewed_at": "now()"
        }).eq("user_id", user_id).eq("paper_id", paper_id).execute()
    except Exception as e:
        print(f"Error marking paper as viewed: {e}")

def mark_all_papers_viewed(user_id):
    """Marks all saved papers as viewed (clears new comment counts)."""
    if not supabase:
        return
    try:
        supabase.table("saved_papers").update({
            "last_viewed_at": "now()"
        }).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"Error marking all papers as viewed: {e}")

def is_favorite(user_id, paper_id):
    """Checks if a paper is already saved."""
    if not supabase:
        return False
    try:
        res = supabase.table("saved_papers").select("id").eq("user_id", user_id).eq("paper_id", paper_id).execute()
        return len(res.data) > 0
    except Exception as e:
        return False

# --- COMMENTS ---

# --- COMMENTS ---

def get_comments(paper_id, user_id=None):
    """Fetches comments for a paper with vote data."""
    if not supabase:
        return []
    try:
        # Use RPC
        res = supabase.rpc("get_comments_with_votes", {
            "p_paper_id": paper_id,
            "p_user_id": user_id
        }).execute()
        
        # Transform for UI compatibility (nested profile)
        cleaned = []
        for row in res.data:
            row['profiles'] = {
                'username': row.get('username'),
                'full_name': row.get('full_name'),
                'avatar_url': row.get('avatar_url')
            }
            cleaned.append(row)
        return cleaned
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return []

def vote_comment(user_id, comment_id, vote_type):
    """
    Casts a vote.
    vote_type: 1 (up), -1 (down), 0 (remove)
    """
    if not supabase: return False
    try:
        if vote_type == 0:
            supabase.table("comment_votes").delete().eq("user_id", user_id).eq("comment_id", comment_id).execute()
        else:
            # Upsert
            supabase.table("comment_votes").upsert({
                "user_id": user_id,
                "comment_id": comment_id,
                "vote_type": vote_type
            }).execute()
        return True
    except Exception as e:
        print(f"Error voting: {e}")
        return False

# --- NOTIFICATIONS & REPLIES ---

def get_notifications(user_id):
    if not supabase: return []
    try:
        # Fetch notifications with the actor's profile
        res = supabase.table("notifications").select(
            "*, actor:profiles!actor_id(username, avatar_url), resource:comments(content, paper_id)"
        ).eq("user_id", user_id).order("created_at", desc=True).limit(20).execute()
        return res.data
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return []

def mark_notification_read(notif_id):
    if not supabase: return False
    try:
        supabase.table("notifications").update({"is_read": True}).eq("id", notif_id).execute()
        return True
    except Exception as e:
        print(f"Error marking notification read: {e}")
        return False

def mark_all_notifications_read(user_id):
    if not supabase: return False
    try:
        supabase.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
        return True
    except Exception as e:
        print(f"Error marking all notifications read: {e}")
        return False

def create_notification(recipient_id, actor_id, resource_id):
    """
    Creates a notification for a user.
    """
    if not supabase: return
    if recipient_id == actor_id: return # Don't notify self
    
    try:
        # Use RPC to bypass RLS
        supabase.rpc("create_notification_safe", {
            "recipient_id": recipient_id,
            "sender_id": actor_id,
            "comment_id": resource_id
        }).execute()
    except Exception as e:
        print(f"Error creating notification: {e}")

def add_comment(user_id, paper_id, content, parent_id=None):
    if not supabase:
        return None
    try:
        data = {
            "user_id": user_id,
            "paper_id": paper_id,
            "content": content
        }
        if parent_id:
            data["parent_id"] = parent_id
            
        res = supabase.table("comments").insert(data).execute()
        
        # logical next step: Check if reply, trigger notification
        if res.data and len(res.data) > 0:
            new_comment = res.data[0]
            new_comment_id = new_comment['id']
            
            if parent_id:
                # 1. Fetch parent comment to get the original author
                parent_res = supabase.table("comments").select("user_id").eq("id", parent_id).single().execute()
                if parent_res.data:
                    parent_author_id = parent_res.data['user_id']
                    # 2. Create Notification
                    create_notification(parent_author_id, user_id, new_comment_id)
            
            return new_comment
        return None
    except Exception as e:
        print(f"Error adding comment: {e}")
        return None
