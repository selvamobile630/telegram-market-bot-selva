from flask import Flask
import threading
import yfinance as yf
import schedule
import time
import requests
from openai import OpenAI
import os
import pytz
from datetime import datetime

# ---------- CONFIG ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- BOT LOGIC ----------
def get_index_summary(ticker, name):
    index = yf.Ticker(ticker)
    hist = index.history(period="1d", interval="1m")
    last_price = hist['Close'][-1]
    open_price = hist['Open'][0]
    change = last_price - open_price
    percent = (change / open_price) * 100
    direction = "positive" if change > 0 else "negative"
    return f"{name}: {last_price:.2f}, {direction} by {change:.2f} points ({percent:.2f}%)"

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
    gainers = [f"{s}: {c:.2f}%" for s, c in sorted_perf[:3]]
    losers = [f"{s}: {c:.2f}%" for s, c in sorted_perf[-3:]]
    return gainers, losers

def generate_reason(summary, gainers, losers):
    prompt = f"""
    Today's Indian stock market summary:
    {summary}.
    
    Top gainers: {', '.join(gainers)}.
    Top losers: {', '.join(losers)}.
    
    Write a 3-4 line brief explanation of why the market was positive or negative today.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

def daily_market_update():
    sensex_summary = get_index_summary("^BSESN", "Sensex")
    nifty_summary = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()
    market_summary = f"{sensex_summary}\n{nifty_summary}"
    reason = generate_reason(market_summary, gainers, losers)
    final_msg = f"📊 Daily Market Update - Bot created by Selvamani:\n{market_summary}\n\n" \
                f"🏆 Top Gainers: {', '.join(gainers)}\n" \
                f"📉 Top Losers: {', '.join(losers)}\n\n" \
                f"📝 Reason:\n{reason}"
    send_telegram(final_msg)
    print("✅ Message sent!")

# ---------- SCHEDULER ----------
def run_scheduler():
    india = pytz.timezone("Asia/Kolkata")

    def job():
        now = datetime.now(india).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Running job at {now} IST")
        daily_market_update()

    # Schedule daily at 5:00 PM IST
    schedule.every().day.at("18:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)

# ---------- FLASK WRAPPER ----------
app = Flask(__name__)

# Run scheduler in a separate daemon thread
threading.Thread(target=run_scheduler, daemon=True).start()

@app.route("/")
def home():
    return "Telegram Market Bot is running!"

if __name__ == "__main__":
    # Render sets the PORT environment variable automatically
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
