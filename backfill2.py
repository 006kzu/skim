import database
import scholar_api
import time


def run_backfill():
    print("🚀 STARTING BACKFILL PROCESS...")

    # 1. Fetch all papers
    papers = database.get_all_papers_raw()
    print(f"📦 Fetched {len(papers)} papers from database.")

    updates_count = 0

    for paper in papers:
        pid = paper.get('id')
        title = paper.get('title')
        current_highlights = paper.get('title_highlights')

        # 2. Check if it needs backfilling
        if current_highlights and len(current_highlights) > 0:
            print(f"⏭️  Skipping (Already has highlights): {title[:30]}...")
            continue

        print(f"⚡ Analyzing: {title[:40]}...")

        # 3. Call AI (Re-using your existing evaluator)
        # We construct a mock 'paper_data' dict that your API expects
        paper_data = {
            'title': title,
            # Use summary as abstract fallback
            'abstract': paper.get('summary') or title
        }

        review = scholar_api.evaluate_paper(paper_data)

        if review and review.get('title_highlights'):
            new_highlights = review['title_highlights']

            # 4. Update Database
            database.update_paper(pid, {'title_highlights': new_highlights})
            print(f"   ✅ Updated with: {new_highlights}")
            updates_count += 1

            # Sleep briefly to be nice to the API rate limits
            time.sleep(1)
        else:
            print("   ❌ Failed to generate highlights.")

    print(f"\n🎉 BACKFILL COMPLETE. Updated {updates_count} papers.")


if __name__ == "__main__":
    run_backfill()
