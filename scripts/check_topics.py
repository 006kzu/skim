from database import get_client
from collections import Counter

client = get_client()
res = client.table("papers").select("topic").execute()

topics = [row['topic'] for row in res.data]
counts = Counter(topics)

print("\n--- DB TOPIC COUNTS ---")
for topic, count in counts.items():
    print(f"'{topic}': {count}")
print("-----------------------")
