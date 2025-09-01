import yfinance as yf
import schedule
import time
import requests
from openai import OpenAI

# ---------- CONFIG: Actual Keys ----------
OPENAI_API_KEY = "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"
TELEGRAM_TOKEN = "8427842986:AAEkQfkJ5NxOtxst8TmHOOp8pdChP2j4qwg"
TELEGRAM_CHAT_ID = "7259834532"

client = OpenAI(api_key=OPENAI_API_KEY)

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
    nifty_stocks = [
        "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
        "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"
    ]
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

    final_msg = f"📊 Daily Market Update( Bot created by Selvamani):\n{market_summary}\n\n"                 f"🏆 Top Gainers: {', '.join(gainers)}\n"                 f"📉 Top Losers: {', '.join(losers)}\n\n"                 f"📝 Reason:\n{reason}"

    send_telegram(final_msg)
    print("✅ Message sent!")

schedule.every().day.at("15:45").do(daily_market_update)

print("⏳ Telegram Market Bot running... will send updates daily at 3:45 PM IST")
while True:
    schedule.run_pending()
    time.sleep(60)
