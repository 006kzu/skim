import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Initialize Client
if url and key:
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
    # We want to send the WHOLE paper object, not just a few fields.
    data = paper.copy()

    # 2. ADD TOPIC
    data['topic'] = search_topic

    # 3. SAFETY CHECKS (Fixing the keys)
    # The API returns 'url', but sometimes your code might look for 'link'
    if 'link' in data and 'url' not in data:
        data['url'] = data.pop('link')  # Rename link -> url

    # Ensure 'url' isn't None (DB requires text usually)
    if not data.get('url'):
        # Fallback if paperId exists
        if data.get('paperId'):
            data['url'] = f"https://www.semanticscholar.org/paper/{data['paperId']}"
        else:
            data['url'] = ""

    # 4. REMOVE ID (Critical Fix)
    # We MUST delete the 'id' field so Supabase generates a new UUID.
    # If we send a title as an ID, it crashes on duplicates.
    if 'id' in data:
        del data['id']

    # 5. INSERT
    try:
        # We use .insert() instead of upsert so we can catch duplicates via the Unique constraint on Title
        response = supabase.table("papers").insert(data).execute()
        print(f"   ✅ DB Saved: {data['title'][:30]}...")
    except Exception as e:
        # Ignore duplicate errors, print others
        if "duplicate key" in str(e):
            print(f"   ⚠️ Skipped (Already in DB): {data['title'][:20]}...")
        else:
            print(f"   ☁️ Cloud DB Error: {e}")


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
