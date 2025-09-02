import os
import requests
import yfinance as yf
from datetime import datetime, timedelta

# Load secrets from environment variables (GitHub Actions Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")

# Hugging Face model (you can change to any text generation model)
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}


def fetch_market_data():
    """Fetch Nifty50 data and some example stocks."""
    indices = {"NSEI": "^NSEI", "SENSEX": "^BSESN"}
    data = {}

    for name, symbol in indices.items():
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) < 2:
            continue

        prev_close = hist["Close"].iloc[-2]
        last_close = hist["Close"].iloc[-1]
        change = ((last_close - prev_close) / prev_close) * 100
        data[name] = {
            "last_close": round(last_close, 2),
            "change": round(change, 2),
        }

    return data


def get_top_movers():
    """Fetch top gainers/losers from example tickers."""
    tickers = ["RELIANCE.NS", "INFY.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    movers = []

    for symbol in tickers:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) < 2:
            continue

        prev_close = hist["Close"].iloc[-2]
        last_close = hist["Close"].iloc[-1]
        change = ((last_close - prev_close) / prev_close) * 100
        movers.append((symbol, round(change, 2)))

    # Sort movers by percentage change
    movers.sort(key=lambda x: x[1], reverse=True)
    gainers = movers[:2]
    losers = movers[-2:]

    return gainers, losers


def generate_reason(market_summary, gainers, losers):
    """Generate a short explanation using Hugging Face API."""
    prompt = f"""
Today’s Indian stock market summary:
Indices: {market_summary}
Top Gainers: {gainers}
Top Losers: {losers}

Explain in 3-4 sentences why the market may have moved this way.
"""

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 200, "temperature": 0.7},
    }

    response = requests.post(HF_API_URL, headers=headers, json=payload)

    # Debug logs
    print("Response status:", response.status_code)
    print("Response text preview:", response.text[:300])

    if response.status_code != 200:
        return f"Error from Hugging Face API: {response.text}"

    try:
        data = response.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        elif isinstance(data, dict) and "error" in data:
            return f"Hugging Face Error: {data['error']}"
        else:
            return str(data)
    except Exception as e:
        return f"Failed to parse HF response: {e}"


def send_to_telegram(message):
    """Send message to Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    resp = requests.post(url, json=payload)
    print("Telegram response:", resp.text)


def daily_market_update():
    """Main job to run every day."""
    market_summary = fetch_market_data()
    gainers, losers = get_top_movers()
    reason = generate_reason(market_summary, gainers, losers)

    today = datetime.now().strftime("%d-%m-%Y")
    message = f"📊 Market Update ({today}) 📊\n\n"
    for idx, vals in market_summary.items():
        message += f"{idx}: {vals['last_close']} ({vals['change']}%)\n"

    message += f"\n🔼 Gainers: {gainers}\n🔽 Losers: {losers}\n\n"
    message += f"📝 Reason: {reason}"

    send_to_telegram(message)


if __name__ == "__main__":
    daily_market_update()
