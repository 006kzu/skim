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
import topics  # <--- NEW IMPORT
import json

# --- ADD THIS HELPER FUNCTION ---


def clean_and_parse_json(raw_text):
    """
    Cleans AI response text to remove Markdown (```json) 
    and returns a safe dictionary.
    """
    # 1. Remove markdown code blocks if present
    clean_text = raw_text.replace("```json", "").replace("```", "").strip()

    # 2. Try to parse the cleaned text
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        print(f"⚠️ JSON PARSING FAILED. Raw text received:\n{raw_text}")
        return {}


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
        description="A catchy, 1-sentence news-style headline.")
    category: str = Field(description="The specific sub-field.")
    # --- NEW FIELDS ---
    key_findings: List[str] = Field(
        description="3-5 bullet points of specific statistics, metrics, or core results (e.g. '95% accuracy', '2x faster').")
    implications: List[str] = Field(
        description="2-3 bullet points on the practical, real-world consequences of this finding.")


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


class QuickPaperReview(BaseModel):
    score: int = Field(
        description="Relevance score from 1-10 based on the 'Filter' criteria")
    layman_summary: str = Field(
        description="A simplified summary of the paper")
    key_findings: str = Field(
        description="Specific numbers or results extracted from the abstract")
    implications: str = Field(
        description="Real-world applications enabled by this research")
    # --- ADD THIS LINE ---
    category: str = Field(
        description="A single-word category for the paper (e.g. 'Robotics', 'Neuroscience', 'Materials')")


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
    1. 'key_findings': Specific numbers or results.
    2. 'implications': What does this enable?
    3. 'layman_summary': A simple summary.
    4. 'category': Classify into one domain (e.g. Bionics, AI, Materials). <--- ADD THIS
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': QuickPaperReview,  # <--- Uses the class defined above
            }
        )
        # The SDK automatically parses the JSON into your Pydantic model
        result = response.parsed.model_dump()

        # Now these keys are guaranteed to exist
        if result['score'] >= 7:
            print(
                f"   🔥 HIGH IMPACT (Score {result['score']}): {result['layman_summary']}")
            print(f"      Findings: {result['key_findings']}")

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
            curated_papers.append({
                "title": paper['title'],
                "date": paper.get('publicationDate', 'Recent'),
                "authors": ", ".join([a['name'] for a in paper.get('authors', [])[:2]]),
                "summary": review['layman_summary'],
                "url": paper.get('url'),
                "journal": paper.get('venue') or "Journal",
                "score": review['score'],
                "category": review['category'],
                "paperId": paper.get('paperId'),
                # --- SAVE NEW DATA ---
                "key_findings": review.get('key_findings', "No key findings available"),
                "implications": review.get('implications', "No implications available")
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
