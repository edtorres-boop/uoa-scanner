import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Top 50 US por market cap - foco liquidez
TICKERS = [
"NVDA","MSFT","AAPL","AMZN","GOOGL","GOOG","META","AVGO","TSLA","BRK-B",
"JPM","LLY","V","UNH","XOM","MA","COST","HD","PG","JNJ",
"NFLX","BAC","CRM","ABBV","ORCL","WMT","AMD","KO","CVX","MRK",
"TMO","ACN","PEP","ADBE","CSCO","LIN","DHR","MCD","WFC","IBM",
"GE","RTX","QCOM","TXN","AMGN","INTU","CAT","NOW","DIS","VZ"
]

MIN_PREMIUM = 100_000
MIN_VOL_OI = 10
EXPIRATIONS_TO_CHECK = 6
MAX_WORKERS = 12

def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def scan_ticker(ticker):
    out = []
    try:
        tk = yf.Ticker(ticker)
        exps = tk.options[:EXPIRATIONS_TO_CHECK]
        spot = tk.history(period="1d")["Close"].iloc[-1]
        for exp in exps:
            time.sleep(0.15)
            try:
                calls = tk.option_chain(exp).calls
                calls = calls[(calls['volume']>0) & (calls['openInterest']>0)].copy()
                calls['vol_oi'] = calls['volume'] / calls['openInterest']
                calls = calls[calls['vol_oi'] >= MIN_VOL_OI]
                for _, r in calls.iterrows():
                    prem = r['volume'] * r['lastPrice'] * 100
                    if prem >= MIN_PREMIUM:
                        out.append({
                            'ticker': ticker,
                            'strike': r['strike'],
                            'exp': exp,
                            'vol': int(r['volume']),
                            'oi': int(r['openInterest']),
                            'ratio': round(r['vol_oi'],1),
                            'premium': int(prem),
                            'spot': round(spot,2),
                            'price': r['lastPrice']
                        })
            except:
                continue
    except:
        pass
    return out

def main():
    now = datetime.now()
    if now.weekday() > 4:
        send_telegram("🏖️ Fim de semana")
        return

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(scan_ticker, t) for t in TICKERS]
        for f in as_completed(futs):
            results.extend(f.result())

    if not results:
        send_telegram(f"✅ Top50 {now.strftime('%H:%M')} - Sem CALLS ≥$100k Vol/OI≥10")
        return

    results.sort(key=lambda x: x['premium'], reverse=True)
    msg = f"🚨 *TOP50 CALLS - ${MIN_PREMIUM/1000:.0f}k+ Vol/OI≥{MIN_VOL_OI}*\n{now.strftime('%d/%m %H:%M')} LIS\n\n"
    for r in results[:12]:
        msg += f"*{r['ticker']}* ${r['spot']} → C${r['strike']} {r['exp']}\n"
        msg += f"Vol:{r['vol']:,} OI:{r['oi']:,} {r['ratio']}x ${r['premium']:,}\n\n"
    
    send_telegram(msg)

if __name__ == "__main__":
    main()
