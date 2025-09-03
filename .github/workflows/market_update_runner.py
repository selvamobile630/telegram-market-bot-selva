import os
import requests
import yfinance as yf
from datetime import datetime

# ---------------- CONFIG ----------------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Example summarization model

# ---------------- MARKET DATA ----------------
def get_index_summary(ticker, name):
    """Fetch official daily open/close data and calculate points change."""
    index = yf.Ticker(ticker)
    hist = index.history(period="1d", interval="1d")
    if hist.empty:
        return f"{name}: Data not available", 0
    open_price = hist['Open'][0]
    close_price = hist['Close'][0]
    change = close_price - open_price
    percent = (change / open_price) * 100
    summary = f"{name} closed at {close_price:.2f} ({'+' if change>=0 else ''}{change:.2f} pts, {'+' if percent>=0 else ''}{percent:.2f}%)"
    return summary, change

def get_top_gainers_losers():
    """Fetch top 3 gainers and losers from a sample Nifty 50 stock list."""
    nifty_stocks = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                    "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
                    "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]
    performance = {}
    for stock in nifty_stocks:
        data = yf.Ticker(stock).history(period="1d")
        if not data.empty:
            open_p = data['Open'][0]
            close_p = data['Close'][0]
            change_pct = ((close_p - open_p) / open_p) * 100
            performance[stock] = change_pct
    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"{s.split('.')[0]} +{c:.2f}%" for s, c in sorted_perf[:3]]
    losers = [f"{s.split('.')[0]} {c:.2f}%" for s, c in sorted_perf[-3:]]
    return gainers, losers

# ---------------- HUGGING FACE REASON ----------------
def generate_reason(summary_text, gainers, losers):
    """Use Hugging Face model to generate 3-4 line reasoning."""
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"Market Summary: {summary_text}\nTop Gainers: {', '.join(gainers)}\nTop Losers: {', '.join(losers)}\n\nExplain in 3-4 lines why the market was positive or negative today."
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code != 200:
            return f"⚠️ Hugging Face API error: {response.text}"

        data = response.json()
        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

# ---------------- TELEGRAM ----------------
def send_to_telegram(message):
    """Send message to Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Telegram API error: {response.text}")
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

# ---------------- MAIN WORKFLOW ----------------
def daily_market_update():
    today_str = datetime.now().strftime("%d %b %Y")
    sensex_summary, sensex_change = get_index_summary("^BSESN", "Sensex")
    nifty_summary, nifty_change = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()

    combined_summary = f"{sensex_summary}\n{nifty_summary}"
    reason = generate_reason(combined_summary, gainers, losers)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {today_str}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{combined_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    daily_market_update()
