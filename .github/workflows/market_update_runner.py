import os
import requests
import yfinance as yf
from datetime import datetime

# ---------- Environment variables ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")

HF_MODEL = "tiiuae/falcon-7b-instruct"  # Instruction-tuned model for explanations

# ---------- Functions ----------
def get_index_summary(ticker, name):
    index = yf.Ticker(ticker)
    hist = index.history(period="1d", interval="1m")
    if hist.empty:
        return f"{name}: Data not available", 0
    last_price = hist['Close'][-1]
    open_price = hist['Open'][0]
    change = last_price - open_price
    percent = (change / open_price) * 100
    return f"{name} closed at {last_price:.2f} ({'+' if change>=0 else ''}{change:.2f} pts, {'+' if percent>=0 else ''}{percent:.2f}%)", change

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
    gainers = [f"{s.split('.')[0]} +{c:.2f}%" for s, c in sorted_perf[:3]]
    losers = [f"{s.split('.')[0]} {c:.2f}%" for s, c in sorted_perf[-3:]]
    return gainers, losers

def generate_reason(summary, gainers, losers):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    prompt = (
        f"Today's Indian stock market summary: {summary}\n"
        f"Top Gainers: {', '.join(gainers)}\n"
        f"Top Losers: {', '.join(losers)}\n\n"
        f"Explain in 3-4 lines why the market went up or down today."
    )
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 150}
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code != 200:
            return f"⚠️ Could not generate explanation: {response.text}"

        data = response.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        return str(data)
    except Exception as e:
        return f"⚠️ Could not generate explanation: {e}"

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

def daily_market_update():
    # Fetch market data
    sensex_summary, sensex_change = get_index_summary("^BSESN", "Sensex")
    nifty_summary, nifty_change = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()

    # Generate explanation
    combined_summary = f"{sensex_summary}\n{nifty_summary}"
    reason = generate_reason(combined_summary, gainers, losers)

    # Build final message
    today = datetime.now().strftime("%d %b %Y")
    final_msg = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {today}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[INFO] Sending message to Telegram...")
    result = send_to_telegram(final_msg)
    print(f"[INFO] Telegram response: {result}")

# ---------- Run ----------
if __name__ == "__main__":
    daily_market_update()
