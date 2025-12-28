import time
import topics
import scholar_api
import database

# Initialize DB
database.init_db()


def run_historical_backfill():
    print("\n" + "="*60)
    print("📜  STARTING HISTORICAL BACKFILL ENGINE (2015-2024)")
    print("    Goal: Populate database with 'Hall of Fame' papers")
    print("="*60 + "\n")

    total_added = 0
    total_topics = len(topics.ALL_TOPICS)

    # Loop through topics with an index so we can show (1/20) etc.
    for i, topic in enumerate(topics.ALL_TOPICS, 1):
        print(f"🔭  [{i}/{total_topics}] Scouting Topic: {topic.upper()}...")

        try:
            # Fetch top 5 most cited papers since 2015
            # We add a small print inside scholar_api usually, but let's be explicit here
            classics = scholar_api.get_historical_feed(
                topic, year_start=2015, limit=5)

            if classics:
                print(f"    ✅  Found {len(classics)} influential papers.")

                for paper in classics:
                    # Print the title being saved (truncated to fit screen)
                    short_title = (
                        paper['title'][:50] + '..') if len(paper['title']) > 50 else paper['title']
                    print(
                        f"       💾  Saving: {short_title} (Cited: {paper.get('citationCount', '?')})")

                    # Save to DB
                    database.save_paper(paper, search_topic=topic)
                    total_added += 1
            else:
                print("    ⚠️  No high-impact papers found for this topic.")

            # Sleep to respect API limits (important!)
            print("    💤  Cooling down API (2s)...")
            time.sleep(2)
            print("")  # Empty line for spacing

        except Exception as e:
            print(f"    ❌  ERROR processing {topic}: {e}\n")

    print("\n" + "="*60)
    print(f"✅  BACKFILL COMPLETE!")
    print(f"    📚  Total Papers Added to Library: {total_added}")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_historical_backfill()
