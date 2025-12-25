import os
import scholar_api
from supabase import create_client

# 1. Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define your topic variable so we can use it later
SEARCH_TOPIC = "Bionics"

# 2. Fetch Papers
print(f"🔎 Scouting topic: {SEARCH_TOPIC}...")
papers = scholar_api.get_curated_feed(topic=SEARCH_TOPIC, limit=1)

# 3. Save to Database
if papers:
    print(f"🚀 Saving {len(papers)} papers...")

    for paper in papers:
        print(f"🔍 DEBUG: Raw URL from API: {paper.get('url')}")
        print(f"🔍 DEBUG: Raw Paper ID: {paper.get('paperId')}")

        # --- FIX 1: TOPIC ---
        # Manually stamp the topic onto the paper data
        paper['topic'] = SEARCH_TOPIC

        # --- FIX 2: AUTHORS ---
        # Semantic Scholar gives a list of objects: [{'name': 'Zach'}, {'name': 'Gemini'}]
        # We need to turn this into a simple string: "Zach, Gemini"
        raw_authors = paper.get('authors', [])
        if isinstance(raw_authors, list):
            # Extract names and join them with commas
            author_names = [a.get('name', '')
                            for a in raw_authors if isinstance(a, dict)]
            paper['authors'] = ", ".join(author_names)

        # --- FIX 3: URL CHECK ---
        # If URL is still empty after this run, we need to check scholar_api.py
        if not paper.get('url') and paper.get('paperId'):
            paper['url'] = f"https://www.semanticscholar.org/paper/{paper['paperId']}"
            print(f"⚠️ URL was missing. Generated fallback: {paper['url']}")

        # Delete the manual ID override (let Supabase handle UUIDs)
        # paper['id'] = ... (Make sure this is deleted/commented out)

        try:
            data, count = supabase.table('papers').insert(paper).execute()
            print(f"✅ Saved: {paper['title'][:40]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
