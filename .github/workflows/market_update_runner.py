import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from transformers import pipeline

# ---------------------------
# Telegram setup
# ---------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ---------------------------
# Scraper functions
# ---------------------------
def scrape_indices():
    url = "https://www.moneycontrol.com/markets/indian-indices/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    # Try to get Sensex and Nifty using CSS classes
    sensex_tag = soup.select_one(".indexBse")  # Moneycontrol class for Sensex
    nifty_tag = soup.select_one(".indexNse")   # Moneycontrol class for Nifty

    sensex = sensex_tag.text.strip() if sensex_tag else "⚠️ Sensex not found"
    nifty = nifty_tag.text.strip() if nifty_tag else "⚠️ Nifty not found"

    return sensex, nifty

def scrape_top_movers():
    headers = {"User-Agent": "Mozilla/5.0"}

    # Top gainers
    url_g = "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.php"
    r_g = requests.get(url_g, headers=headers, timeout=10)
    soup_g = BeautifulSoup(r_g.text, "html.parser")
    gainers = [t.text.strip() for t in soup_g.select("table tr td a")][:5]

    # Top losers
    url_l = "https://www.moneycontrol.com/stocks/marketstats/nseloser/index.php"
    r_l = requests.get(url_l, headers=headers, timeout=10)
    soup_l = BeautifulSoup(r_l.text, "html.parser")
    losers = [t.text.strip() for t in soup_l.select("table tr td a")][:5]

    # Fallback if empty
    gainers = gainers if gainers else ["⚠️ Gainers not found"]
    losers = losers if losers else ["⚠️ Losers not found"]

    return gainers, losers

# ---------------------------
# Summarization using BART
# ---------------------------
def generate_summary(text):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    try:
        summary = summarizer(text, max_length=150, min_length=50, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        return f"⚠️ Could not generate summary: {e}"

# ---------------------------
# Telegram sender
# ---------------------------
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")

# ---------------------------
# Main function
# ---------------------------
if __name__ == "__main__":
    today = datetime.now().strftime("%d %b %Y")

    try:
        sensex, nifty = scrape_indices()
        gainers, losers = scrape_top_movers()
        combined_text = f"{sensex}\n{nifty}\nTop Gainers: {', '.join(gainers)}\nTop Losers: {', '.join(losers)}"
        reason = generate_summary(combined_text)

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
