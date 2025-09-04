import os
import yfinance as yf
from datetime import datetime, timedelta
from transformers import pipeline
import requests

# ---------------------------
# Telegram setup
# ---------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ---------------------------
# Fetch Sensex and Nifty
# ---------------------------
def fetch_indices():
    today = datetime.now()
    yesterday = today - timedelta(days=3)  # to ensure last trading day

    # ^BSESN = Sensex, ^NSEI = Nifty 50
    sensex = yf.Ticker("^BSESN")
    nifty = yf.Ticker("^NSEI")

    sensex_hist = sensex.history(start=yesterday.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))
    nifty_hist = nifty.history(start=yesterday.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))

    if len(sensex_hist) >= 2:
        sensex_yesterday = sensex_hist["Close"][-2]
        sensex_today = sensex_hist["Close"][-1]
    else:
        sensex_yesterday = sensex_today = sensex_hist["Close"][0]

    if len(nifty_hist) >= 2:
        nifty_yesterday = nifty_hist["Close"][-2]
        nifty_today = nifty_hist["Close"][-1]
    else:
        nifty_yesterday = nifty_today = nifty_hist["Close"][0]

    sensex_points = sensex_today - sensex_yesterday
    nifty_points = nifty_today - nifty_yesterday

    sensex_summary = f"Sensex: {sensex_today:.2f} ({sensex_points:+.2f} pts, {(sensex_points/sensex_yesterday)*100:+.2f}%)"
    nifty_summary = f"Nifty 50: {nifty_today:.2f} ({nifty_points:+.2f} pts, {(nifty_points/nifty_yesterday)*100:+.2f}%)"

    return sensex_summary, nifty_summary

# ---------------------------
# Fetch Top Gainers / Losers
# ---------------------------
def fetch_top_stocks():
    # Example: Top 10 NSE stocks (can be adjusted)
    stocks = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
              "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
              "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]

    performance = {}
    for s in stocks:
        hist = yf.Ticker(s).history(period="1d")
        if not hist.empty:
            open_p = hist['Open'][0]
            close_p = hist['Close'][-1]
            change_pct = ((close_p - open_p)/open_p)*100
            performance[s.replace(".NS","")] = change_pct

    sorted_perf = sorted(performance.items(), key=lambda x: x[1], reverse=True)
    gainers = [f"{s}: {c:+.2f}%" for s, c in sorted_perf[:5]]
    losers = [f"{s}: {c:+.2f}%" for s, c in sorted_perf[-5:]]
    return gainers, losers

# ---------------------------
# Summarization using BART
# ---------------------------
def generate_summary(sensex, nifty, gainers, losers):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    combined_text = f"{sensex}\n{nifty}\nTop Gainers: {', '.join(gainers)}\nTop Losers: {', '.join(losers)}"
    try:
        summary = summarizer(combined_text, max_length=150, min_length=50, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        return f"⚠️ Could not generate summary: {e}"

# ---------------------------
# Send Telegram
# ---------------------------
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload)
        print("[INFO] Telegram response:", r.text)
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    today = datetime.now().strftime("%d %b %Y")
    sensex, nifty = fetch_indices()
    gainers, losers = fetch_top_stocks()
    reason = generate_summary(sensex, nifty, gainers, losers)

    message = f"""
Bot created by Selvamani
📅 Date: {today}

📈 Daily Market Update

{sensex}
{nifty}

🏆 Top Gainers: {', '.join(gainers)}
📉 Top Losers: {', '.join(losers)}

🤔 Reason:
{reason}
"""
    send_to_telegram(message.strip())
