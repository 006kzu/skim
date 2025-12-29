import scholar_api
import os
from dotenv import load_dotenv

# 1. Force load .env to ensure keys are present
load_dotenv()


def test_ai_connection():
    print("="*40)
    print("🧪  AI ISOLATION TEST")
    print("="*40)

    # Check Key
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("❌ CRITICAL: GOOGLE_API_KEY is missing from environment!")
        return
    print(f"✅ API Key found: {key[:5]}...{key[-3:]}")

    # 2. Define a Dummy Paper (Known Good Data)
    test_paper = {
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train."
    }

    print(f"\n📨 Sending Test Paper: '{test_paper['title']}'")

    try:
        # 3. Call the function
        result = scholar_api.evaluate_paper(test_paper)

        print("\n🔍  RAW RESULT FROM AI:")
        print(result)

        if result and result.get('key_findings'):
            print("\n✅  SUCCESS: AI is extracting data correctly.")
        else:
            print("\n⚠️  WARNING: AI returned a result, but lists are empty.")

    except Exception as e:
        print(f"\n❌  EXCEPTION: {e}")


if __name__ == "__main__":
    test_ai_connection()
