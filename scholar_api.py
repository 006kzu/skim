import requests
import datetime
import random
import time
import arxiv
import os
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import topics  # <--- NEW IMPORT

load_dotenv()

# --- CONFIGURATION ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY not found in .env or environment variables!")
else:
    print(f"✅ Google API Key loaded (starts with {api_key[:5]}...)")

client = genai.Client(api_key=api_key)

# --- DATA STRUCTURES ---


class QuickPaperReview(BaseModel):
    score: int = Field(
        description="Score 1-10 based on wider population impact.")
    is_major: bool = Field(
        description="True ONLY if the research fundamentally changes how we interact with the world.")
    layman_summary: str = Field(
        description="A catchy, 1-sentence news-style headline focusing on the real-world benefit.")
    category: str = Field(description="The specific sub-field.")

# --- SEMANTIC SCHOLAR (FEED) LOGIC ---


def fetch_with_retry(url, params, retries=3, backoff_factor=2):
    print(
        f"📡 Connecting to Semantic Scholar... (Query: {params.get('query')})")
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json().get('data', [])
                print(
                    f"✅ Connection successful. Retrieved {len(data)} raw papers.")
                return data
            elif response.status_code == 429:
                wait_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                print(f"⚠️ Rate limited. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Error: Status Code {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Network Exception: {e}")
            return []
    return []


def evaluate_paper(paper):
    """
    Your 'Ruthless Editor' Logic.
    """
    if not paper.get('abstract'):
        return None

    venue = paper.get('venue') or "Unknown"
    print(f"🤖 AI Reviewing: '{paper['title'][:50]}...'")

    prompt = f"""
    You are a ruthless Scientific Editor for "Peripheral News."
    Your Goal: Prioritize the reader's time by filtering out insignificant research.

    ### THE GOLDEN RULE OF SIGNIFICANCE
    To determine if a paper is worth reading, you must ask this specific question:
    "Does this impact affect the population OUTSIDE of this specific domain, or does it help experts in this domain DIRECTLY impact the outside population?"

    ### SCORING RUBRIC (1-10)
    
    **SCORES 1-5: INSIGNIFICANT (REJECT)**
    - Criteria: The impact is trapped inside the domain.
    
    **SCORE 6: DOMAIN RELEVANT (BORDERLINE)**
    - Criteria: Solid science, but the downstream impact on humanity is vague or too distant.
    
    **SCORE 7: IMPACTFUL (PUBLISH)**
    - Criteria: Clear potential to affect the outside world.

    **SCORES 8-10: TRANSFORMATIVE (MAJOR INNOVATION)**
    - Criteria: A breakthrough that will undeniably change safety, health, energy, or understanding of the universe.

    ### YOUR TASK
    Analyze the paper below. If it is "Insignificant," score it low (1-5). If it passes the Golden Rule, score it high (7+).
    
    Paper Data:
    - Title: {paper['title']}
    - Venue: {venue}
    - Abstract: {paper['abstract']}
    
    Output JSON.
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
        print(f"   ↳ Score: {result['score']}/10 | Cat: {result['category']}")
        return result
    except Exception as e:
        print(f"❌ AI Review failed: {e}")
        return None


def get_curated_feed(topic=None, limit=5):
    """
    Fetches papers. If topic is None, it AUTO-SCOUTS a random topic from topics.py.
    """
    # --- AUTO-SCOUT LOGIC ---
    if not topic:
        topic = random.choice(topics.ALL_TOPICS)
        print(f"\n🎲 AUTO-SCOUT ACTIVATED: Scouting topic '{topic}'")
    else:
        print(f"\n🎯 TARGETED SCOUT: Scouting topic '{topic}'")

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    current_year = datetime.datetime.now().year

    params = {
        "query": topic,
        "year": f"{current_year-1}-{current_year}",
        "sort": "publicationDate:desc",
        "fields": "title,abstract,url,publicationDate,venue,authors",
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
            paper['ai_data'] = review
            curated_papers.append({
                "title": paper['title'],
                "date": paper.get('publicationDate', 'Recent'),
                "authors": ", ".join([a['name'] for a in paper.get('authors', [])[:2]]),
                "summary": review['layman_summary'],
                "link": paper.get('url'),
                "journal": paper.get('venue') or "Journal",
                "score": review['score'],
                "category": review['category']
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
