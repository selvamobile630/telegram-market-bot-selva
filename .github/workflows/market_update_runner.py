import os
import requests
import yfinance as yf
from datetime import datetime, timedelta

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")
HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

# ---------- FETCH MARKET DATA ----------
def fetch_sensex_nifty():
    sensex = yf.Ticker("^BSESN")
    nifty = yf.Ticker("^NSEI")

    today = datetime.now()
    yesterday = today - timedelta(days=2)  # Ensure we get last 2 trading days

    # Fetch daily history
    sensex_hist = sensex.history(start=yesterday.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))
    nifty_hist = nifty.history(start=yesterday.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))

    # Closing prices
    yesterday_sensex = sensex_hist["Close"][-2] if len(sensex_hist) >= 2 else sensex_hist["Close"][0]
    today_sensex = sensex_hist["Close"][-1]
    points_sensex = today_sensex - yesterday_sensex
    percent_sensex = (points_sensex / yesterday_sensex) * 100

    yesterday_nifty = nifty_hist["Close"][-2] if len(nifty_hist) >= 2 else nifty_hist["Close"][0]
    today_nifty = nifty_hist["Close"][-1]
    points_nifty = today_nifty - yesterday_nifty
    percent_nifty = (points_nifty / yesterday_nifty) * 100

    sensex_summary = f"Sensex: {today_sensex:.2f} ({points_sensex:+.2f} pts, {percent_sensex:+.2f}%)"
    nifty_summary = f"Nifty 50: {today_nifty:.2f} ({points_nifty:+.2f} pts, {percent_nifty:+.2f}%)"

    return sensex_summary, nifty_summary, points_sensex, points_nifty

def fetch_top_gainers_losers():
    nifty_stocks = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                    "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
                    "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]
    performance = {}
    for stock in nifty_stocks:
        data = yf.Ticker(stock).history(period="1d")
        if not data.empty:
            open_p = data['Open'][0]
            close_p = data['Close'][-1]
            change_pct = ((close_p - open_p) / open_p) * 100
            performance[stock.replace(".NS","")] = change_pct
    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"{s}: {c:+.2f}%" for s, c in sorted_perf[:5]]
    losers = [f"{s}: {c:+.2f}%" for s, c in sorted_perf[-5:]]
    return gainers, losers

# ---------- GENERATE REASON ----------
def generate_reason(summary, gainers, losers):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"Market Summary: {summary}\nTop Gainers: {', '.join(gainers)}\nTop Losers: {', '.join(losers)}\n\nWrite a brief 3-4 line explanation of why the market was positive or negative today."
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            raise Exception(f"Hugging Face API error: {response.text}")

        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        elif isinstance(data, dict) and "error" in data:
            raise Exception(f"Hugging Face returned error: {data['error']}")
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

# ---------- SEND TO TELEGRAM ----------
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Telegram API error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

# ---------- DAILY MARKET UPDATE ----------
def daily_market_update():
    sensex_summary, nifty_summary, points_sensex, points_nifty = fetch_sensex_nifty()
    gainers, losers = fetch_top_gainers_losers()
    reason = generate_reason(f"{sensex_summary}, {nifty_summary}", gainers, losers)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

# ---------- RUN SCRIPT ----------
if __name__ == "__main__":
    daily_market_update()
