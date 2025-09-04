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
    yesterday = today - timedelta(days=3)

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

    # Emojis for index direction
    sensex_emoji = "📈" if sensex_points >= 0 else "📉"
    nifty_emoji = "📈" if nifty_points >= 0 else "📉"

    sensex_summary = f"{sensex_emoji} Sensex: {sensex_today:.2f} ({sensex_points:+.2f} pts, {(sensex_points/sensex_yesterday)*100:+.2f}%)"
    nifty_summary = f"{nifty_emoji} Nifty 50: {nifty_today:.2f} ({nifty_points:+.2f} pts, {(nifty_points/nifty_yesterday)*100:+.2f}%)"

    return sensex_summary, nifty_summary

# ---------------------------
# Fetch Top Gainers / Losers
# ---------------------------
def fetch_top_stocks():
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

    # Emojis for Telegram
    gainers = [f"🟢 {s}: {c:+.2f}%" for s, c in sorted_perf[:5]]
    losers = [f"🔴 {s}: {c:+.2f}%" for s, c in sorted_perf[-5:]]

    biggest_gainer = gainers[0] if gainers else "N/A"
    biggest_loser = losers[-1] if losers else "N/A"

    return gainers, losers, biggest_gainer, biggest_loser

# ---------------------------
# Generate professional summary
# ---------------------------
def generate_summary(sensex, nifty, gainers, losers, biggest_gainer, biggest_loser):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    
    # Format gainers and losers for summary
    gainers_text = ", ".join([g.split(" ",1)[1] for g in gainers])  # remove emoji for clean text
    losers_text = ", ".join([l.split(" ",1)[1] for l in losers])

    combined_text = (
        f"{sensex}\n{nifty}\n"
        f"Top Gainers: {gainers_text}\n"
        f"Top Losers: {losers_text}\n\n"
        f"Highlight: Biggest Gainer: {biggest_gainer.split(' ',1)[1]}, Biggest Loser: {biggest_loser.split(' ',1)[1]}"
    )

    try:
        summary = summarizer(combined_text, max_length=180, min_length=70, do_sample=False)
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
    gainers, losers, biggest_gainer, biggest_loser = fetch_top_stocks()
    reason = generate_summary(sensex, nifty, gainers, losers, biggest_gainer, biggest_loser)

    message = f"""
Bot created by Selvamani
📅 Date: {today}

📈 Daily Market Update

{sensex}
{nifty}

🏆 Top Gainers:
{chr(10).join(gainers)}

📉 Top Losers:
{chr(10).join(losers)}

🤔 Reason:
{reason}
"""
    send_to_telegram(message.strip())
