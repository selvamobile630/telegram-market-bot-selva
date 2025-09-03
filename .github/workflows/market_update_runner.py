import os
import requests
import yfinance as yf
from datetime import datetime

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "facebook/bart-large-cnn"  # Hugging Face summarization model

# ---------- FETCH SENSEX ----------
def get_sensex_google():
    """
    Fetch Sensex index data (current and today's change) from Google Finance.
    """
    try:
        url = "https://www.google.com/finance/quote/BSESN:INDEXBOM"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers)
        text = response.text

        import re
        match = re.search(
            r'\"BSESN:INDEXBOM\",\"price\":([0-9.]+),\"change\":([\-0-9.]+),\"change_percent\":([\-0-9.]+)',
            text
        )
        if match:
            close_price = float(match.group(1))
            change = float(match.group(2))
            percent = float(match.group(3))
            summary = f"Sensex closed at {close_price:.2f} ({'+' if change >=0 else ''}{change:.2f} pts, {'+' if percent >=0 else ''}{percent:.2f}%)"
            return summary, change
        else:
            return "Sensex: Data not found", 0
    except Exception as e:
        return f"Sensex: Error fetching data ({e})", 0

# ---------- FETCH NIFTY ----------
def get_nifty_yf():
    ticker = "^NSEI"
    index = yf.Ticker(ticker)
    hist = index.history(period="1d")
    if hist.empty:
        return "Nifty 50: Data not found"
    last_price = hist['Close'][-1]
    open_price = hist['Open'][0]
    change = last_price - open_price
    percent = (change / open_price) * 100
    return f"Nifty 50 closed at {last_price:.2f} ({'+' if change>=0 else ''}{change:.2f} pts, {'+' if percent>=0 else ''}{percent:.2f}%)"

# ---------- TOP 5 GAINERS/LOSERS ----------
def get_top_gainers_losers():
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
            performance[stock] = change_pct
    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"{s.split('.')[0]} +{c:.2f}%" for s, c in sorted_perf[:5]]
    losers = [f"{s.split('.')[0]} {c:+.2f}%" for s, c in sorted_perf[-5:]]
    return gainers, losers

# ---------- GENERATE REASON ----------
def generate_reason(summary_text):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": summary_text}

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
            return f"⚠️ Hugging Face returned error: {data['error']}"
        else:
            return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

# ---------- SEND TELEGRAM ----------
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

# ---------- DAILY MARKET UPDATE ----------
def daily_market_update():
    today_date = datetime.now().strftime("%d %b %Y")
    sensex_summary, sensex_change = get_sensex_google()
    nifty_summary = get_nifty_yf()
    gainers, losers = get_top_gainers_losers()

    summary_text = (
        f"Sensex change today: {sensex_change:+.2f} pts\n"
        f"{sensex_summary}\n{nifty_summary}\n"
        f"Top Gainers: {', '.join(gainers)}\n"
        f"Top Losers: {', '.join(losers)}"
    )

    reason = generate_reason(summary_text)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {today_date}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n"
        f"{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(message)
    print(f"[INFO] Telegram response: {result}")

# ---------- MAIN ----------
if __name__ == "__main__":
    daily_market_update()
