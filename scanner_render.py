import yfinance as yf, pandas as pd, requests, os, datetime as dt
import pandas_market_calendars as mcal

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TICKERS = ["NVDA","TSLA","AAPL","MSFT","AMZN","META","AMD","GOOGL","SPY","QQQ"]

def envia(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

nyse = mcal.get_calendar('NYSE')
hoje = pd.Timestamp.now(tz='America/New_York').date()
if hoje not in nyse.valid_days(start_date=hoje, end_date=hoje):
    envia(f"ℹ️ {hoje} — Bolsa fechada.")
    exit()

resultados = []
for t in TICKERS:
    try:
        tk = yf.Ticker(t)
        for exp in tk.options[:2]:
            calls = tk.option_chain(exp).calls
            calls = calls[(calls['volume']>0) & (calls['openInterest']>0)]
            for _, r in calls.iterrows():
                vol_oi = r['volume']/r['openInterest']
                premio = r['volume']*r['lastPrice']*100
                if vol_oi>=3 and premio>400000:
                    resultados.append({'ticker':t,'strike':r['strike'],'exp':exp,'premio':int(premio),'vol_oi':round(vol_oi,1)})
    except: pass

hora = dt.datetime.now(dt.timezone(dt.timedelta(hours=1))).strftime("%H:%M")
if resultados:
    df = pd.DataFrame(resultados).sort_values('premio',ascending=False).head(5)
    msg = f"🚨 *UOA {hora} PT*\n"
    for _,r in df.iterrows():
        msg += f"\n• *{r['ticker']}* {r['strike']}C {r['exp']} | ${r['premio']:,} | Vol/OI {r['vol_oi']}x"
else:
    msg = f"✅ {hora} PT — Sem fluxo relevante."
envia(msg)