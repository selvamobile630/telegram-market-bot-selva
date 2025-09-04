import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from openai import OpenAI

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Your GPT API key

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- SCRAPE RAW DATA ----------
def scrape_moneycontrol():
    url = "https://www.moneycontrol.com/markets/indian-indices/"
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.content, "html.parser")
    raw_text = soup.get_text(separator="\n")
    return raw_text[:5000]

def scrape_gainers_losers():
    url_g = "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.php"
    url_l = "https://www.moneycontrol.com/stocks/marketstats/nseloser/index.php"

    response_g = requests.get(url_g, timeout=10)
    soup_g = BeautifulSoup(response_g.content, "html.parser")
    gainers_text = soup_g.get_text(separator="\n")

    response_l = requests.get(url_l, timeout=10)
    soup_l = BeautifulSoup(response_l.content, "html.parser")
    losers_text = soup_l.get_text(separator="\n")

    return gainers_text[:5000], losers_text[:5000]

# ---------- PROCESS WITH GPT ----------
def fetch_sensex_with_gpt():
    try:
        raw_data = scrape_moneycontrol()
        prompt = (
            "Here is raw scraped text from Moneycontrol containing Sensex and Nifty data:\n\n"
            f"{raw_data}\n\n"
            "Extract ONLY today's Sensex and Nifty values in this format:\n"
            "Sensex: XXXX.XX (+/-YY.YY pts, +/-Z.ZZ%)\n"
            "Nifty 50: XXXX.XX (+/-YY.YY pts, +/-Z.ZZ%)"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        reply = response.choices[0].message.content.strip()
        lines = reply.split("\n")
        sensex_summary = lines[0] if len(lines) > 0 else "⚠️ Sensex data not available"
        nifty_summary = lines[1] if len(lines) > 1 else "⚠️ Nifty data not available"

        return sensex_summary, nifty_summary
    except Exception as e:
        return f"⚠️ Error fetching Sensex ({e})", f"⚠️ Error fetching Nifty ({e})"

def fetch_gainers_losers_with_gpt():
    try:
        raw_gainers, raw_losers = scrape_gainers_losers()
        prompt = (
            "Here is raw scraped data from Moneycontrol.\n\n"
            f"Top Gainers Data:\n{raw_gainers}\n\n"
            f"Top Losers Data:\n{raw_losers}\n\n"
            "Extract the **Top 5 Gainers and Top 5 Losers** with percentage change in this format:\n"
            "🏆 Top Gainers: STOCK1 (+X.XX%), STOCK2 (+X.XX%), ...\n"
            "📉 Top Losers: STOCK1 (-X.XX%), STOCK2 (-X.XX%), ..."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        reply = response.choices[0].message.content.strip()
        lines = reply.split("\n")
        gainers = lines[0] if lines else "⚠️ Gainers not available"
        losers = lines[1] if len(lines) > 1 else "⚠️ Losers not available"

        return gainers, losers
    except Exception as e:
        return f"⚠️ Error fetching gainers ({e})", f"⚠️ Error fetching losers ({e})"

def generate_reason_with_gpt(sensex_summary, nifty_summary, gainers, losers):
    try:
        prompt = (
            f"Market Summary:\n{sensex_summary}\n{nifty_summary}\n\n"
            f"{gainers}\n{losers}\n\n"
            "Based on this data, write a short 3-4 line explanation of why the Indian stock market "
            "was positive or negative today. Mention key sectors or stocks influencing the move."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Could not generate explanation ({e})"

# ---------- TELEGRAM SEND ----------
def send_to_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
        print("⚠️ Telegram credentials missing")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        print("[DEBUG] Telegram Response:", response.text)
        return response.json()
    except Exception as e:
        print(f"⚠️ Telegram send failed: {e}")
        return None

# ---------- DAILY MARKET UPDATE ----------
def daily_market_update():
    sensex_summary, nifty_summary = fetch_sensex_with_gpt()
    gainers, losers = fetch_gainers_losers_with_gpt()
    reason = generate_reason_with_gpt(sensex_summary, nifty_summary, gainers, losers)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"{gainers}\n{losers}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[DEBUG] Final Message:\n", message)
    send_to_telegram(message)

# ---------- RUN ----------
if __name__ == "__main__":
    daily_market_update()
