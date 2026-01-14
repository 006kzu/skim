import os
from supabase import create_client
from dotenv import load_dotenv

# Load env variables
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_KEY in .env file")
    exit(1)

print(f"DEBUG: Testing connection to: {url}")

try:
    supabase = create_client(url, key)
    
    print("Attempting to initiate Twitter OAuth...")
    data = supabase.auth.sign_in_with_oauth({
        "provider": "twitter",
        "options": {
            "redirect_to": "http://localhost:8080/auth/callback"
        }
    })
    
    print("\n✅ SUCCESS! Supabase returned a URL:")
    print(f"Auth URL: {data.url}")
    print("\nIf you see this, your Supabase Project IS configured correctly and the issue was likely caching or environment variables in the main app.")

except Exception as e:
    print("\n❌ FAILED. Supabase returned an error:")
    print(e)
    print("\nDIAGNOSIS:")
    if "provider is not enabled" in str(e):
        print("1. The 'Twitter' provider is definitely DISABLED in the Supabase Dashboard for this specific Project URL.")
        print("2. OR you are connecting to the wrong Project URL (check .env vs Dashboard).")
