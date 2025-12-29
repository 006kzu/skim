import time
import database
import scholar_api


def run_database_repair():
    print("\n" + "="*60)
    print("🔧  DATABASE REPAIR TOOL")
    print("    Scanning Supabase for papers with missing 'Key Findings'...")
    print("="*60 + "\n")

    # 1. Fetch all papers from Supabase
    all_papers = database.get_all_papers_raw()
    total_papers = len(all_papers)
    print(f"📦  Loaded {total_papers} papers from database.\n")

    updates_count = 0

    for index, paper in enumerate(all_papers):
        # 2. Check for missing data
        # We check if key_findings is None (null) or an empty list []
        missing_findings = not paper.get('key_findings')
        missing_implications = not paper.get('implications')

        if missing_findings or missing_implications:
            print(
                f"🔸  [{index+1}/{total_papers}] Needs Repair: {paper.get('title')[:40]}...")

            # 3. Prepare data for AI
            # We try to use 'abstract', but fallback to 'summary' if abstract is missing
            text_content = paper.get('abstract') or paper.get('summary')

            # --- DEBUG: CHECK TEXT QUALITY ---
            if not text_content:
                print("      ⚠️  Skipping: No text content found (None/Empty).")
                continue

            # Print a snippet so we know what the AI is actually reading
            print(
                f"      📖 Reading ({len(str(text_content))} chars): {str(text_content)[:100]}...")
            # ---------------------------------

            if len(text_content) < 50:
                print("      ⚠️  Skipping: Content too short to analyze.")
                continue

            # Construct the object scholar_api expects
            paper_input = {
                'title': paper.get('title'),
                'abstract': text_content
            }

            # 4. Run AI Analysis
            # We use your existing function from scholar_api
            new_data = scholar_api.evaluate_paper(paper_input)

            if new_data:
                # 5. Prepare the Update Payload
                # We ONLY send the fields we want to change
                updates = {
                    "key_findings": new_data.get('key_findings', []),
                    "implications": new_data.get('implications', []),
                    "category": new_data.get('category'),
                    "score": new_data.get('score'),
                    "summary": new_data.get('layman_summary')
                }

                # PRINT DEBUG: Verify we actually have data before sending
                print(
                    f"      📝 Generated Findings: {len(updates['key_findings'])} items")

                # 6. Push Update to Supabase
                # We use the paper's existing unique 'id'
                database.update_paper(paper['id'], updates)
                updates_count += 1

                # Sleep briefly to avoid rate limits (Google Gemini & Supabase)
                time.sleep(1.5)
            else:
                print("      ❌  AI failed to generate data.")

    print("\n" + "="*60)
    print(f"✅  REPAIR COMPLETE")
    print(f"    Total Records Updated: {updates_count}")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_database_repair()
