import os
import requests

# Read secrets from GitHub Actions environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

def fetch_market_summary():
    """Dummy market data generator (replace with real API if available)."""
    return {
        "summary": "Indian stock market closed mixed today.",
        "gainers": ["Reliance +2.3%", "Infosys +1.8%", "HDFC Bank +1.2%"],
        "losers": ["TCS -1.5%", "ICICI Bank -0.9%", "ONGC -0.7%"]
    }

def generate_reason(summary, gainers, losers):
    """Call Hugging Face API to generate reasoning."""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"Market Summary: {summary}\nTop Gainers: {gainers}\nTop Losers: {losers}\n\nExplain why this happened:"
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        print(f"[DEBUG] HuggingFace status: {response.status_code}")
        if response.status_code == 401:
            raise Exception("❌ Invalid Hugging Face token. Please check HF_API_KEY.")
        if response.status_code != 200:
            raise Exception(f"❌ Hugging Face API error: {response.text}")

        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        elif isinstance(data, dict) and "error" in data:
            raise Exception(f"❌ Hugging Face returned error: {data['error']}")
        else:
            return str(data)

    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

def send_to_telegram(message):
    """Send message to Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"[DEBUG] Telegram status: {response.status_code}")
        if response.status_code != 200:
            raise Exception(f"❌ Telegram API error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

def daily_market_update():
    """Main workflow: fetch data, summarize, and send message."""
    market = fetch_market_summary()
    reason = generate_reason(market["summary"], market["gainers"], market["losers"])

    message = (
        f"📈 *Daily Market Update*\n\n"
        f"Summary: {market['summary']}\n\n"
        f"Top Gainers: {', '.join(market['gainers'])}\n"
        f"Top Losers: {', '.join(market['losers'])}\n\n"
        f"🤔 Reason: {reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

if __name__ == "__main__":
    daily_market_update()
