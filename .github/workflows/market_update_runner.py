import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ---------- CONFIG ----------
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_KEY = os.environ.get("HF_API_KEY")
HF_MODEL = "facebook/bart-large-cnn"

# ---------- FETCH SENSEX/NIFTY DATA ----------
def fetch_sensex_nifty_moneycontrol():
    urls = {
        "Sensex": "https://www.moneycontrol.com/markets/indian-indices/bse-sensex-9.html",
        "Nifty": "https://www.moneycontrol.com/markets/indian-indices/nifty-50-9.html"
    }
    
    summaries = {}
    
    for index, url in urls.items():
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")
            
            main_value_tag = soup.find("div", class_="PT10 PB10")
            if main_value_tag:
                current_value_text = main_value_tag.find("strong").text.strip().replace(",", "")
                current_value = float(current_value_text)
                
                change_tag = main_value_tag.find("span", class_="value_change")
                if change_tag:
                    change_text = change_tag.text.strip().replace(",", "")
                    if "(" in change_text and ")" in change_text:
                        pts = float(change_text.split("(")[0])
                        pct = float(change_text.split("(")[1].replace(")", "").replace("%", ""))
                    else:
                        pts, pct = 0.0, 0.0
                else:
                    pts, pct = 0.0, 0.0
                
                summaries[index] = f"{index}: {current_value:.2f} ({pts:+.2f} pts, {pct:+.2f}%)"
            else:
                summaries[index] = f"{index}: ⚠️ Data not found"
        except Exception as e:
            summaries[index] = f"{index}: ⚠️ Error fetching data ({e})"
    
    print("[DEBUG] Sensex/Nifty:", summaries)
    return summaries.get("Sensex", "⚠️ Sensex error"), summaries.get("Nifty", "⚠️ Nifty error")

# ---------- FETCH TOP GAINERS/LOSERS FROM MONEYCONTROL ----------
def fetch_top_gainers_losers_moneycontrol():
    url = "https://www.moneycontrol.com/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=9"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        gainers, losers = [], []

        # Gainers
        table_rows = soup.select("table#indicesTopGainers tr")
        for row in table_rows[1:6]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                name = cols[0].text.strip()
                change_pct = cols[2].text.strip()
                gainers.append(f"{name}: {change_pct}")

        # Losers
        table_rows = soup.select("table#indicesTopLosers tr")
        for row in table_rows[1:6]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                name = cols[0].text.strip()
                change_pct = cols[2].text.strip()
                losers.append(f"{name}: {change_pct}")

        if not gainers: gainers = ["⚠️ No gainers data"]
        if not losers: losers = ["⚠️ No losers data"]

        print("[DEBUG] Gainers:", gainers)
        print("[DEBUG] Losers:", losers)

        return gainers, losers
    except Exception as e:
        return [f"⚠️ Error fetching gainers ({e})"], [f"⚠️ Error fetching losers ({e})"]

# ---------- GENERATE REASON ----------
def generate_reason(summary, gainers, losers):
    if not HF_API_KEY:
        return "⚠️ Hugging Face API key missing."

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {
        "inputs": f"Market Summary: {summary}\nTop Gainers: {', '.join(gainers)}\nTop Losers: {', '.join(losers)}\n\nWrite a brief 3-4 line explanation of why the market was positive or negative today."
    }

    try:
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        data = response.json()
        print("[DEBUG] Hugging Face Response:", data)

        if isinstance(data, list) and "summary_text" in data[0]:
            return data[0]["summary_text"]
        else:
            return "⚠️ Could not generate explanation"
    except Exception as e:
        return f"⚠️ HF API error: {e}"

# ---------- SEND TO TELEGRAM ----------
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
    sensex_summary, nifty_summary = fetch_sensex_nifty_moneycontrol()
    gainers, losers = fetch_top_gainers_losers_moneycontrol()
    reason = generate_reason(f"{sensex_summary}, {nifty_summary}", gainers, losers)

    message = (
        f"🤖 Bot created by Selvamani\n"
        f"📅 Date: {datetime.now().strftime('%d %b %Y')}\n\n"
        f"📈 Daily Market Update\n\n"
        f"{sensex_summary}\n{nifty_summary}\n\n"
        f"🏆 Top Gainers: {', '.join(gainers)}\n"
        f"📉 Top Losers: {', '.join(losers)}\n\n"
        f"🤔 Reason:\n{reason}"
    )

    print("[DEBUG] Final Message:\n", message)
    send_to_telegram(message)

# ---------- RUN SCRIPT ----------
if __name__ == "__main__":
    daily_market_update()
