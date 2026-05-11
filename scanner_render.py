import yfinance as yf, pandas as pd, os, requests, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TICKERS = ["NVDA","MSFT","AAPL","AMZN","GOOGL","GOOG","META","AVGO","TSLA","BRK-B",
"JPM","LLY","V","UNH","XOM","MA","COST","HD","PG","JNJ","NFLX","BAC","CRM","ABBV",
"ORCL","WMT","AMD","KO","CVX","MRK","TMO","ACN","PEP","ADBE","CSCO","LIN","DHR",
"MCD","WFC","IBM","GE","RTX","QCOM","TXN","AMGN","INTU","CAT","NOW","DIS","VZ"]

MIN_PREMIUM = 100_000
MIN_VOL_OI = 10
EXPIRATIONS = 6
WORKERS = 5   # menos workers = menos bloqueio Yahoo

def tg(msg):
    print("TELEGRAM:", msg[:80])
    if not TELEGRAM_TOKEN: return
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=15)
        print("TG status", r.status_code)
    except Exception as e:
        print("TG error", e)

def scan(t):
    out=[]
    try:
        tk=yf.Ticker(t)
        exps = tk.options[:EXPIRATIONS]
        spot = tk.history(period="1d")["Close"].iloc[-1]
        for exp in exps:
            time.sleep(0.4)  # dá respiro ao Yahoo
            try:
                calls = tk.option_chain(exp).calls
                calls = calls[(calls.volume>0)&(calls.openInterest>0)].copy()
                calls['r'] = calls.volume/calls.openInterest
                calls = calls[calls.r >= MIN_VOL_OI]
                for _,r in calls.iterrows():
                    prem = r.volume * r.lastPrice * 100
                    if prem >= MIN_PREMIUM:
                        out.append({'t':t,'s':r.strike,'e':exp,'v':int(r.volume),'o':int(r.openInterest),'x':round(r.r,1),'p':int(prem),'spot':round(spot,2)})
            except Exception as e:
                print(t, exp, "erro", e)
    except Exception as e:
        print(t, "falhou", e)
    return out

def main():
    now=datetime.now()
    if now.weekday()>4:
        tg("🏖️ Fim de semana"); return
    res=[]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs=[ex.submit(scan,t) for t in TICKERS]
        for f in as_completed(futs): res.extend(f.result())
    print("Total encontrados:", len(res))
    if not res:
        tg(f"✅ Top50 {now.strftime('%H:%M')} - Sem CALLS (Yahoo pode ter bloqueado)")
        return
    res.sort(key=lambda x:x['p'], reverse=True)
    msg=f"🚨 *TOP50* {now.strftime('%H:%M')}\n"
    for r in res[:10]:
        msg+=f"{r['t']} C{r['s']} {r['e']} ${r['p']:,} {r['x']}x\n"
    tg(msg)

if __name__=="__main__": main()
