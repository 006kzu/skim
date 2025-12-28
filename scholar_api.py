import requests
import datetime
import random
import time
import arxiv
from typing import List
import os
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import topics
import json

# --- HELPER: JSON CLEANER ---


def clean_and_parse_json(raw_text):
    """
    Cleans AI response text to remove Markdown (```json) 
    and returns a safe dictionary.
    """
    clean_text = raw_text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print(f"⚠️ JSON PARSING FAILED. Raw text received:\n{raw_text}")
        return {}


load_dotenv()

# --- CONFIGURATION ---
google_api_key = os.getenv("GOOGLE_API_KEY")
s2_api_key = os.getenv("S2_API_KEY")  # <--- NEW: Semantic Scholar Key

if not google_api_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env or environment variables!")

client = genai.Client(api_key=google_api_key)

# --- DATA SCHEMA ---
# Consolidated into ONE correct class matching your Database


class QuickPaperReview(BaseModel):
    score: int = Field(
        description="Score 1-10 based on wider population impact.")
    layman_summary: str = Field(
        description="A catchy, 1-sentence news-style headline.")
    category: str = Field(
        description="The specific sub-field (e.g. 'Robotics', 'Neuroscience').")
    key_findings: List[str] = Field(
        description="3-5 bullet points of specific statistics, metrics, or core results.")
    implications: List[str] = Field(
        description="2-3 bullet points on the practical, real-world consequences.")

# --- SEMANTIC SCHOLAR (FEED) LOGIC ---


def fetch_with_retry(url, params, retries=3, backoff_factor=2):
    print(
        f"📡 Connecting to Semantic Scholar... (Query: {params.get('query')})")

    # Authenticate to avoid Rate Limiting
    headers = {}
    if s2_api_key:
        headers["x-api-key"] = s2_api_key

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json().get('data', [])
                print(
                    f"✅ Connection successful. Retrieved {len(data)} raw papers.")
                return data
            elif response.status_code == 429:
                wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                print(f"⚠️ Rate limited. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            elif response.status_code == 403:
                print("❌ 403 Forbidden: Your S2_API_KEY might be invalid.")
                return []
            else:
                print(f"❌ Error: Status Code {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Network Exception: {e}")
            return []
    return []


def evaluate_paper(paper):
    if not paper.get('abstract'):
        return None

    print(f"🤖 AI Reviewing: '{paper['title'][:50]}...'")

    prompt = f"""
    You are a ruthless Scientific Editor for "Peripheral News."
    
    Analyze this paper based on the following data:
    - Title: {paper['title']}
    - Abstract: {paper['abstract']}
    
    ### TASK 1: THE FILTER (Score 1-10)
    Assign a 'score' based on impact:
    - 1-5: Insignificant (Internal academic chatter).
    - 6-7: Impactful (Real-world usage).
    - 8-10: Transformative (Civilization-level shift).

    ### TASK 2: EXTRACTION
    Extract these details:
    1. 'key_findings': A LIST of specific numbers or results.
    2. 'implications': A LIST of what this enables.
    3. 'layman_summary': A simple summary.
    4. 'category': Classify into one domain (e.g. Bionics, AI, Materials).
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': QuickPaperReview,
            }
        )
        result = response.parsed.model_dump()

        if result['score'] >= 7:
            print(
                f"   🔥 HIGH IMPACT (Score {result['score']}): {result['layman_summary']}")

        return result

    except Exception as e:
        print(f"❌ AI Review failed: {e}")
        return None


def get_curated_feed(topic=None, limit=5):
    """
    Fetches papers. If topic is None, it AUTO-SCOUTS a random topic from topics.py.
    """
    if not topic:
        topic = random.choice(topics.ALL_TOPICS)
        print(f"\n🎲 AUTO-SCOUT ACTIVATED: Scouting topic '{topic}'")
    else:
        print(f"\n🎯 TARGETED SCOUT: Scouting topic '{topic}'")

    url = "[https://api.semanticscholar.org/graph/v1/paper/search](https://api.semanticscholar.org/graph/v1/paper/search)"
    current_year = datetime.datetime.now().year

    params = {
        "query": topic,
        "year": f"{current_year-1}-{current_year}",
        "sort": "publicationDate:desc",
        # Added paperId explicitly
        "fields": "title,abstract,url,publicationDate,venue,authors,paperId",
        "limit": limit * 2
    }

    raw_papers = fetch_with_retry(url, params)
    curated_papers = []

    for paper in raw_papers:
        if not paper.get('abstract'):
            continue

        review = evaluate_paper(paper)

        if review and review['score'] >= 7:
            print("   🔥 KEEPING PAPER (High Impact)")

            # Format authors safely
            author_list = paper.get('authors', [])
            author_str = ", ".join(
                [a['name'] for a in author_list[:2]]) if author_list else "Unknown"

            curated_papers.append({
                "title": paper['title'],
                "date": paper.get('publicationDate', 'Recent'),
                "authors": author_str,
                "summary": review['layman_summary'],
                "url": paper.get('url'),
                "journal": paper.get('venue') or "Journal",
                "score": review['score'],
                "category": review['category'],
                "paperId": paper.get('paperId'),
                # Use empty lists [] as default for JSONB compatibility
                "key_findings": review.get('key_findings', []),
                "implications": review.get('implications', [])
            })
        else:
            print("   🗑️ Discarding (Low Impact)")

        if len(curated_papers) >= limit:
            print(f"✅ Limit reached ({limit} papers). Stopping.")
            break

    return curated_papers

# --- ARXIV (SEARCH) LOGIC ---


def search_arxiv(query, max_results=6):
    print(f"🔎 Searching ArXiv for: '{query}'")
    search = arxiv.Search(query=query, max_results=max_results,
                          sort_by=arxiv.SortCriterion.SubmittedDate)
    results = []
    try:
        for result in search.results():
            results.append({
                "title": result.title,
                "date": result.published.strftime("%Y-%m-%d"),
                "authors": ", ".join([a.name for a in result.authors[:3]]),
                "summary": result.summary.replace("\n", " "),
                "link": result.pdf_url,
                "journal": "arXiv Pre-print"
            })
        print(f"✅ Found {len(results)} results on ArXiv.")
    except Exception as e:
        print(f"❌ ArXiv Error: {e}")
        pass
    return results


def analyze_with_ai(paper_title, paper_abstract):
    """Deep dive skim for a specific paper."""
    print(f"⚡ Skimming specific paper: {paper_title[:30]}...")
    prompt = f"""
    Provide a "Skim" summary for:
    Title: {paper_title}
    Abstract: {paper_abstract}
    
    Structure:
    1. 🎯 Core Innovation (1 sentence)
    2. ⚙️ Technical Mechanism
    3. 🚀 Impact on Engineering/Bionics
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', contents=prompt)
        print("✅ Skim complete.")
        return response.text
    except Exception as e:
        print(f"❌ Skim Error: {e}")
        return f"Error: {e}"
