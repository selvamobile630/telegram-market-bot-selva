import os
import requests
import yfinance as yf
from datetime import datetime, timedelta

# Environment variables from GitHub Actions / local env
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

# List of some Nifty 50 stocks to track (expandable)
NIFTY_STOCKS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", 
                "ICICIBANK.NS", "SBIN.NS", "ONGC.NS"]

def fetch_market_summary():
    """Fetch live Nifty and Sensex data with top movers."""
    try:
        # --- Sensex Data ---
        sensex = yf.Ticker("^BSESN")
        hist_sensex = sensex.history(period="1d")
        open_sensex = hist_sensex["Open"].iloc[-1]
        close_sensex = hist_sensex["Close"].iloc[-1]
        change_points = close_sensex - open_sensex
        change_pct = (change_points / open_sensex) * 100

        sensex_summary = f"Sensex closed at {close_sensex:.2f} ({change_points:+.2f} pts, {change_pct:+.2f}%)"

        # --- Nifty 50 Index Data ---
        nifty = yf.Ticker("^NSEI")
        hist_nifty = nifty.history(period="1d")
        open_nifty = hist_nifty["Open"].iloc[-1]
        close_nifty = hist_nifty["Close"].iloc[-1]
        change_nifty = close_nifty - open_nifty
        pct_nifty = (change_nifty / open_nifty) * 100
        nifty_summary = f"Nifty 50 closed at {close_nifty:.2f} ({change_nifty:+.2f} pts, {pct_nifty:+.2f}%)"

        # --- Top Movers ---
        movers = {}
        for symbol in NIFTY_STOCKS:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                o = hist["Open"].iloc[-1]
                c = hist["Close"].iloc[-1]
                pct = ((c - o) / o) * 100
                movers[symbol] = pct

        sorted_movers = sorted(movers.items(), key=lambda x: x[1], reverse=True)
        top_gainers = [f"{s.replace('.NS','')} {p:+.2f}%" for s, p in sorted_movers[:3]]
        top_losers = [f"{s.replace('.NS','')} {p:+.2f}%" for s, p in sorted_movers[-3:]]

        return {
            "sensex_summary": sensex_summary,
            "nifty_summary": nifty_summary,
            "gainers": top_gainers,
            "losers": top_losers
        }

    except Exception as e:
        return {
            "sensex_summary": f"⚠️ Could not fetch Sensex data: {e}",
            "nifty_summary": f"⚠️ Could not fetch Nifty data: {e}",
            "gainers": [],
            "losers": []
        }

def generate_reason(sensex_summary, nifty_summary, gainers, losers):
    """Generate reasoning using Hugging Face summarization model."""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    prompt = (
        f"Sensex: {sensex_summary}\n"
        f"Nifty 50: {nifty_summary}\n"
        f"Top Gainers: {gainers}\n"
        f"Top Losers: {losers}\n\n"
        "Write a brief 3-4 line explanation why the market was positive or negative today."
    )
    payload = {"inputs": prompt}

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            raise Exception(f"❌ Hugging Face API error: {response.text}")

        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"].strip()
        elif isinstance(data, dict) and "error" in data:
            raise Exception(f"❌ Hugging Face returned error: {data['error']}")
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

def send_to_telegram(message):
    """Send message to Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            raise Exception(f"❌ Telegram API error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

def daily_market_update():
    """Fetch data, summarize, and send message."""
    # IST date
    now_utc = datetime.utcnow()
    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = now_utc + ist_offset
    date_str = now_ist.strftime("%d %b %Y")

    market = fetch_market_summary()
    reason = generate_reason(market["sensex_summary"], market["nifty_summary"], market["gainers"], market["losers"])

    message = (
        f"*🤖 Bot created by Selvamani*\n"
        f"📅 Date: {date_str}\n\n"
        f"📈 *Daily Market Update*\n\n"
        f"{market['sensex_summary']}\n"
        f"{market['nifty_summary']}\n\n"
        f"🏆 Top Gainers: {', '.join(market['gainers']) if market['gainers'] else 'N/A'}\n"
        f"📉 Top Losers: {', '.join(market['losers']) if market['losers'] else 'N/A'}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

if __name__ == "__main__":
    daily_market_update()
