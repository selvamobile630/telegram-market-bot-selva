import os
import requests
from datetime import datetime
from transformers import pipeline

# ---------------------------
# Telegram setup
# ---------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ---------------------------
# Fetch Sensex/Nifty via Moneycontrol API
# ---------------------------
def fetch_sensex_nifty():
    headers = {"User-Agent": "Mozilla/5.0"}

    # Sensex
    sensex_json = requests.get(
        "https://priceapi.moneycontrol.com/pricefeed/indices/indianindices/11",
        headers=headers, timeout=10
    ).json()
    sensex_val = sensex_json["data"]["lastPrice"]
    sensex_change = sensex_json["data"]["pChange"]
    sensex = f"Sensex: {sensex_val} ({sensex_change:+.2f}%)"

    # Nifty
    nifty_json = requests.get(
        "https://priceapi.moneycontrol.com/pricefeed/indices/indianindices/9",
        headers=headers, timeout=10
    ).json()
    nifty_val = nifty_json["data"]["lastPrice"]
    nifty_change = nifty_json["data"]["pChange"]
    nifty = f"Nifty 50: {nifty_val} ({nifty_change:+.2f}%)"

    return sensex, nifty

# ---------------------------
# Fetch Top 5 Gainers / Losers via API
# ---------------------------
def fetch_gainers_losers():
    headers = {"User-Agent": "Mozilla/5.0"}

    gainers_json = requests.get(
        "https://priceapi.moneycontrol.com/pricefeed/topgainerslosers/nse/gainers",
        headers=headers, timeout=10
    ).json()
    losers_json = requests.get(
        "https://priceapi.moneycontrol.com/pricefeed/topgainerslosers/nse/losers",
        headers=headers, timeout=10
    ).json()

    gainers = [f"{item['company']} ({item['changePercent']}%)" for item in gainers_json["data"][:5]]
    losers = [f"{item['company']} ({item['changePercent']}%)" for item in losers_json["data"][:5]]

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
# Send message to Telegram
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

    try:
        sensex, nifty = fetch_sensex_nifty()
        gainers, losers = fetch_gainers_losers()
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
    except Exception as e:
        message = f"⚠️ Failed to fetch market update: {e}"

    send_to_telegram(message.strip())
