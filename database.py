import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Initialize Client
# If keys are missing (e.g. GitHub Actions didn't load secrets yet), this handles it gracefully
if url and key:
    supabase: Client = create_client(url, key)
else:
    supabase = None
    print("⚠️ WARNING: Supabase keys not found. Database features will fail.")


def init_db():
    """
    Legacy compatibility. 
    Supabase tables are created via the web dashboard SQL editor, 
    so we don't need to create tables here anymore.
    """
    pass


def save_paper(paper, search_topic):
    """Saves a paper to Supabase Cloud."""
    if not supabase:
        return

    data = {
        "id": paper['title'],  # Unique ID
        "title": paper['title'],
        "url": paper['link'],
        "summary": paper['summary'],
        "score": paper['score'],
        "category": paper['category'],
        "topic": search_topic
    }

    try:
        # .upsert() inserts, or updates if the ID already exists
        response = supabase.table("papers").upsert(data).execute()
    except Exception as e:
        print(f"☁️ Cloud DB Error: {e}")


def get_papers_by_topic(topic, limit=10):
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
            .order("date_added", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"Error fetching top hits: {e}")
        return []


def get_recent_papers(limit=10):
    """Fallback fetch."""
    if not supabase:
        return []

    try:
        response = supabase.table("papers") \
            .select("*") \
            .order("date_added", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        return []
