import os
import requests
import yfinance as yf

# Environment variables (from GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")

# ---------- MARKET DATA ----------
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
    nifty_stocks = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                    "INFY.NS", "TCS.NS", "HINDUNILVR.NS",
                    "KOTAKBANK.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS"]
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

# ---------- HUGGING FACE LLM ----------
def generate_reason(summary, gainers, losers):
    prompt = f"""
    Today's Indian stock market summary:
    {summary}.
    
    Top gainers: {', '.join(gainers)}.
    Top losers: {', '.join(losers)}.
    
    Write a 3-4 line brief explanation of why the market was positive or negative today.
    """
    url = "https://api-inference.huggingface.co/models/NousResearch/Llama-2-7b-chat-hf"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": prompt}
    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    if "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    else:
        return "Could not generate market summary today."

# ---------- TELEGRAM ----------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload)

# ---------- DAILY UPDATE ----------
def daily_market_update():
    sensex_summary = get_index_summary("^BSESN", "Sensex")
    nifty_summary = get_index_summary("^NSEI", "Nifty 50")
    gainers, losers = get_top_gainers_losers()
    market_summary = f"{sensex_summary}\n{nifty_summary}"
    reason = generate_reason(market_summary, gainers, losers)
    final_msg = f"📊 Daily Market Update - Bot created by Selvamani:\n{market_summary}\n\n" \
                f"🏆 Top Gainers: {', '.join(gainers)}\n" \
                f"📉 Top Losers: {', '.join(losers)}\n\n" \
                f"📝 Reason:\n{reason}"
    send_telegram(final_msg)
    print("✅ Message sent!")

if __name__ == "__main__":
    daily_market_update()
