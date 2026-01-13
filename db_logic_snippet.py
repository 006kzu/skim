
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

def create_notification(recipient_id, actor_id, resource_id):
    """
    Creates a notification for a user.
    """
    if not supabase: return
    if recipient_id == actor_id: return # Don't notify self
    
    try:
        supabase.table("notifications").insert({
            "user_id": recipient_id,
            "actor_id": actor_id,
            "resource_id": resource_id
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
