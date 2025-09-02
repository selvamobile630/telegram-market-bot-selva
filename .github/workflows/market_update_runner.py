import yfinance as yf
import requests
from datetime import datetime

# Telegram credentials from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(url, data=payload)
    if r.status_code == 200:
        print("✅ Telegram message sent.")
    else:
        print(f"❌ Failed to send message: {r.text}")

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
    return f"{name}: {last_price:.2f}, {direction} by {change:.2f} pts ({percent:.2f}%)"

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
    gainers = [f"{s}: {c:.2f}%" for s, c in sorted_perf[:3]]
    losers = [f"{s}: {c:.2f}%" for s, c in sorted_perf[-3:]]
    return gainers, losers

def compose_message():
    sensex_summary = get_index_summary("^BSESN", "Sensex")
    nifty_summary = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()

    msg = (
        f"📊 Daily Market Update Bot created by Selvamani - India\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"📅 Date: {datetime.now().strftime('%d-%m-%Y')}"
    )
    return msg

if __name__ == "__main__":
    message = compose_message()
    send_telegram_message(message)
