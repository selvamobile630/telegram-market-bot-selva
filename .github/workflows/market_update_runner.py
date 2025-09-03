import os
import requests
import yfinance as yf
from datetime import datetime

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

# ---------- FETCH MARKET DATA ----------
def fetch_sensex_nifty():
    sensex = yf.Ticker("^BSESN")
    nifty = yf.Ticker("^NSEI")

    sensex_hist = sensex.history(period="1d")
    nifty_hist = nifty.history(period="1d")

    last_sensex = sensex_hist["Close"][-1]
    open_sensex = sensex_hist["Open"][0]
    points_sensex = last_sensex - open_sensex
    percent_sensex = (points_sensex / open_sensex) * 100

    last_nifty = nifty_hist["Close"][-1]
    open_nifty = nifty_hist["Open"][0]
    points_nifty = last_nifty - open_nifty
    percent_nifty = (points_nifty / open_nifty) * 100

    sensex_summary = f"Sensex: {last_sensex:.2f} ({points_sensex:+.2f} pts, {percent_sensex:+.2f}%)"
    nifty_summary = f"Nifty 50: {last_nifty:.2f} ({points_nifty:+.2f} pts, {percent_nifty:+.2f}%)"

    return sensex_summary, nifty_summary, points_sensex, points_nifty

def fetch_top_gainers_losers():
    # Example Nifty 50 tickers
    nifty_tickers = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                     "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
                     "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]

    performance = {}
    for ticker in nifty_tickers:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            open_p = data["Open"][0]
            close_p = data["Close"][-1]
            change_pct = ((close_p - open_p) / open_p) * 100
            performance[ticker] = change_pct

    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"{t.split('.')[0]} +{v:.2f}%" for t, v in sorted_perf[:5]]
    losers = [f"{t.split('.')[0]} {v:.2f}%" for t, v in sorted_perf[-5:]]

    return gainers, losers

# ---------- GENERATE REASON ----------
def generate_reason(sensex_summary, nifty_summary, gainers, losers):
    prompt = f"""
Market Summary:
{sensex_summary}
{nifty_summary}

Top Gainers: {', '.join(gainers)}
Top Losers: {', '.join(losers)}

Explain in 3-4 lines why the market went up or down today.
"""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
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
            return f"⚠️ Hugging Face error: {data['error']}"
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Could not generate reason: {e}"

# ---------- SEND TO TELEGRAM ----------
def send_to_telegram(message):
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

# ---------- DAILY MARKET UPDATE ----------
def daily_market_update():
    sensex_summary, nifty_summary, sensex_points, nifty_points = fetch_sensex_nifty()
    gainers, losers = fetch_top_gainers_losers()
    reason = generate_reason(sensex_summary, nifty_summary, gainers, losers)

    date_str = datetime.now().strftime("%d %b %Y")
    message = (
        f"🤖 Bot created by Selvamani\n📅 Date: {date_str}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

# ---------- RUN ----------
if __name__ == "__main__":
    daily_market_update()
