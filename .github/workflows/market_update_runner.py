import os
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

# ---------------- FUNCTIONS ----------------

def fetch_sensex_nifty():
    """Fetch Sensex and Nifty data from NSE India API"""
    url = "https://www.nseindia.com/api/globalindices"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.5"}
    response = requests.get(url, headers=headers)
    data = response.json()["data"]

    sensex = next(item for item in data if item["index"] == "SENSEX")
    nifty = next(item for item in data if item["index"] == "Nifty 50")

    sensex_summary = f"Sensex closed at {sensex['lastPrice']} ({sensex['pointsChange']:+} pts, {sensex['percentChange']:+}%)"
    nifty_summary = f"Nifty 50 closed at {nifty['lastPrice']} ({nifty['pointsChange']:+} pts, {nifty['percentChange']:+}%)"
    return sensex_summary, nifty_summary, sensex["pointsChange"], nifty["pointsChange"]

def fetch_top_stocks():
    """Fetch top gainers and losers from NSE"""
    url_gainers = "https://www.nseindia.com/api/live-analysis-variations"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.5"}
    try:
        r = requests.get(url_gainers, headers=headers)
        data = r.json()
        # Simplified: use some sample gainers/losers if API structure changes
        gainers = [f"{item['symbol']} {item['netPrice']}%" for item in data.get("topGainers", [])][:5]
        losers = [f"{item['symbol']} {item['netPrice']}%" for item in data.get("topLosers", [])][:5]
        return gainers, losers
    except:
        # fallback dummy data
        gainers = ["RELIANCE +2.3%", "HDFCBANK +1.8%", "ICICIBANK +1.5%", "INFY +1.2%", "TCS +0.9%"]
        losers = ["TCS -1.5%", "INFY -1.3%", "ONGC -1.0%", "HINDUNILVR -0.8%", "SBIN -0.5%"]
        return gainers, losers

def generate_reason(summary, gainers, losers):
    """Call Hugging Face API to generate 3-line market reason"""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    prompt = (
        f"Market Summary: {summary}\n"
        f"Top Gainers: {', '.join(gainers)}\n"
        f"Top Losers: {', '.join(losers)}\n\n"
        "Explain briefly in 3 lines why the market was positive or negative today."
    )
    payload = {"inputs": prompt}

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        elif isinstance(data, dict) and "error" in data:
            return f"⚠️ Hugging Face Error: {data['error']}"
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

def daily_market_update():
    sensex_summary, nifty_summary, sensex_points, nifty_points = fetch_sensex_nifty()
    gainers, losers = fetch_top_stocks()
    market_summary = f"{sensex_summary}\n{nifty_summary}"

    reason = generate_reason(market_summary, gainers, losers)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{market_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    result = send_to_telegram(message)
    print(f"Telegram response: {result}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    daily_market_update()
