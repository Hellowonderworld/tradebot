import os, yfinance as yf, pandas as pd, pandas_ta as ta, requests, time, csv
from datetime import datetime

# 專家系統參數
CAPITAL = 2500        # 本金
RISK_PCT = 0.05       # 單筆風險 5%

class TradingExpert:
    def analyze(self, m):
        score = 0
        if m['sma10'] > m['sma60']: score += 30
        if 40 <= m['rsi'] <= 65: score += 20
        if m['vol'] > m['avg_vol'] * 1.3: score += 20
        if m['price'] > m['high20']: score += 20
        
        if m['adx'] < 20: return None # 過濾盤整
        
        if score >= 60:
            risk_amt = CAPITAL * RISK_PCT
            dist = m['price'] - m['low20']
            dist = dist if dist > 0 else m['price'] * 0.03
            shares = int(risk_amt / dist)
            cost = shares * m['price']
            if shares > 0 and cost <= CAPITAL:
                return f"✅ [訊號] 分數:{score}, 建議買:{shares}股, 成本約:{cost:.0f}"
            elif shares > 0:
                return f"⚠️ [預算不足] 分數:{score}, 需{cost:.0f}元"
        return None

def fetch_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period='6mo')
        if len(df) < 60: return None
        df.ta.sma(length=10, append=True); df.ta.sma(length=60, append=True)
        df.ta.rsi(length=14, append=True); df.ta.adx(length=14, append=True)
        l = df.iloc[-1]
        return {
            'price': l['Close'], 'sma10': l['SMA_10'], 'sma60': l['SMA_60'],
            'rsi': l['RSI_14'], 'adx': l['ADX_14'], 'vol': l['Volume'],
            'avg_vol': df['Volume'].tail(20).mean(),
            'high20': df['High'].tail(20).max(), 'low20': df['Low'].tail(20).min()
        }
    except: return None

def send_line(msg):
    token = os.environ.get("LINE_ACCESS_TOKEN")
    uid = os.environ.get("LINE_USER_ID")
    if not token or not uid: return print(msg)
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": uid, "messages": [{"type": "text", "text": msg}]}
    requests.post(url, json=payload, headers=headers)

def main():
    bot = TradingExpert()
    results = [f"📊 {datetime.now().strftime('%Y-%m-%d')} 量化掃描報告"]
    
    with open('my_universe.csv', 'r') as f:
        symbols = [s for row in csv.reader(f) for s in row]

    for s in symbols:
        data = fetch_data(s)
        if data:
            res = bot.analyze(data)
            if res: results.append(f"• {s.split('.')[0]}: {res}")
        time.sleep(0.6)

    send_line("\n".join(results) if len(results) > 1 else "今日無符合條件標的。")

if __name__ == "__main__":
    main()