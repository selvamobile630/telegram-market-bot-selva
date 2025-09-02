import yfinance as yf
import requests
from datetime import datetime
import os
from openai import OpenAI

# Environment variables (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# Telegram sender (MarkdownV2)
# -------------------------
def send_telegram_message(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2"
    }
    r = requests.post(url, data=payload)
    if r.status_code == 200:
        print("✅ Telegram message sent.")
    else:
        print(f"❌ Failed to send message: {r.text}")

# -------------------------
# Market data
# -------------------------
def get_index_summary(ticker, name):
    index = yf.Ticker(ticker)
    hist = index.history(period="1d")
    if hist.empty:
        return f"{name}: Data unavailable"
    last_price = hist['Close'][-1]
    open_price = hist['Open'][0]
    change = last_price - open_price
    percent = (change / open_price) * 100
    direction = "positive" if change > 0 else "negative"
    emoji = "🟢" if change > 0 else "🔴"
    return f"{emoji} *{name}*: {last_price:.2f}, {'+' if change>=0 else ''}{change:.2f} pts ({percent:.2f}%)"

def get_top_gainers_losers():
    nifty_stocks = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                    "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
                    "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]
    performance = {}
    for stock in nifty_stocks:
        data = yf.Ticker(stock).history(period="1d")
        if data.empty:
            continue
        open_p = data['Open'][0]
        close_p = data['Close'][-1]
        change_pct = ((close_p - open_p) / open_p) * 100
        performance[stock] = change_pct
    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"🟢 {s}: {c:.2f}%" for s, c in sorted_perf[:3]]
    losers = [f"🔴 {s}: {c:.2f}%" for s, c in sorted_perf[-3:]]
    return gainers, losers

# -------------------------
# GPT-4O reasoning
# -------------------------
def generate_market_reason(summary, gainers, losers):
    prompt = f"""
    Today's Indian stock market summary:
    {summary}.
    
    Top gainers: {', '.join(gainers)}.
    Top losers: {', '.join(losers)}.
    
    Write a brief 3-4 line explanation of why the market was positive or negative today.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

# -------------------------
# Compose final Telegram message
# -------------------------
def compose_message():
    sensex_summary = get_index_summary("^BSESN", "Sensex")
    nifty_summary = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()
    reason = generate_market_reason(f"{sensex_summary}\n{nifty_summary}", gainers, losers)

    msg = (
        f"*📊 Daily Market Update - India*\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"*🏆 Top Gainers:*\n" + "\n".join(gainers) + "\n\n"
        f"*📉 Top Losers:*\n" + "\n".join(losers) + "\n\n"
        f"*📝 Reason:*\n{reason}\n"
        f"*📅 Date:* {datetime.now().strftime('%d-%m-%Y')}"
    )

    # Escape special characters for MarkdownV2
    escape_chars = ['.', '-', '+', '(', ')', ':']
    for ch in escape_chars:
        msg = msg.replace(ch, f"\\{ch}")
    return msg

# -------------------------
# Run daily update
# -------------------------
if __name__ == "__main__":
    message = compose_message()
    send_telegram_message(message)
