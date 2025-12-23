import schedule
import time
import topics
import scholar_api
import database
import os
import sys

# Initialize DB
database.init_db()


def perform_nightly_scan():
    print("\n🌙 MIDNIGHT PROTOCOL INITIATED: Starting Batch Scan...")

    for topic in topics.ALL_TOPICS:
        print(f"   🔭 Scouting: {topic}...")
        try:
            new_papers = scholar_api.get_curated_feed(topic, limit=3)
            if new_papers:
                print(f"      ✅ Found {len(new_papers)} papers.")
                for paper in new_papers:
                    # We save with the specific topic tag
                    database.save_paper(paper, search_topic=topic)
            else:
                print("      ❌ No significant papers.")

            # Sleep slightly to be polite to the API
            time.sleep(2)

        except Exception as e:
            print(f"      ⚠️ Error scouting {topic}: {e}")

    print("🌞 PROTOCOL COMPLETE. Database updated.")


if __name__ == "__main__":
    # Check if we are running in a GitHub Action
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("🤖 Detected GitHub Actions environment. Running once...")
        perform_nightly_scan()
        sys.exit(0)  # Exit cleanly so the Action finishes
    else:
        # Local Mode: Keep the schedule loop
        print("🕰️  Local Scout Agent running. Waiting for midnight...")
        schedule.every().day.at("00:00").do(perform_nightly_scan)

        while True:
            schedule.run_pending()
            time.sleep(60)
