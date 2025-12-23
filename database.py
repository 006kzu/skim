import sqlite3

DB_NAME = "skim.db"


def init_db():
    """Creates the table with the new 'topic' column."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT,
            url TEXT,
            summary TEXT,
            score INTEGER,
            category TEXT,
            topic TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def save_paper(paper, search_topic):
    """Saves a paper and tags it with the Search Topic (e.g. 'Bionics')."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO papers (id, title, url, summary, score, category, topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            paper['title'],
            paper['title'],
            paper['link'],
            paper['summary'],
            paper['score'],
            paper['category'],  # The AI's specific sub-category
            search_topic       # The broad Sidebar topic
        ))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()


def get_papers_by_topic(topic, limit=10):
    """Fetches papers specifically for the clicked sidebar topic."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT * FROM papers 
        WHERE topic = ? 
        ORDER BY date_added DESC LIMIT ?
    ''', (topic, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_papers(limit=10):
    """Fallback for the main page (mixed feed)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM papers ORDER BY date_added DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_top_rated_papers(limit=8):
    """
    Fetches the absolute highest-scoring papers across ALL topics.
    Sorts by Score first, then Recency.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Logic: Get papers with score >= 7, sorted by score (descending), then date
    c.execute('''
        SELECT * FROM papers 
        WHERE score >= 7 
        ORDER BY score DESC, date_added DESC 
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
