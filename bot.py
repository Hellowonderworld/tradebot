import os, yfinance as yf, pandas as pd, requests, time, csv
from datetime import datetime

CAPITAL = 16000
RISK_PCT = 0.05

class DualExpert:
    def analyze(self, m):
        # --- 做多邏輯 ---
        l_score = 0
        if m['price'] > m['sma10'] > m['sma60']: l_score += 40
        if 40 <= m['rsi'] <= 65: l_score += 20
        if m['vol'] > m['avg_vol'] * 1.2: l_score += 20
        if m['price'] > m['high20']: l_score += 20
        
        if l_score >= 60 and m['adx'] > 18:
            dist = m['price'] - m['low20']
            dist = dist if dist > 0 else m['price'] * 0.03
            shares = int((CAPITAL * RISK_PCT) / dist)
            if 0 < (shares * m['price']) <= CAPITAL:
                return f"🚀 [做多] 分數:{l_score}, 建議買:{shares}股, 守:{m['low20']:.1f}"

        # --- 放空邏輯 ---
        s_score = 0
        if m['price'] < m['sma10'] < m['sma60']: s_score += 40
        bias = (m['price'] - m['sma60']) / m['sma60']
        if s_score >= 40 and bias > -0.08 and m['price'] < m['low20']:
            atr_stop = m['price'] + (2 * m['atr'])
            stop_p = min(m['high20'], atr_stop)
            dist = stop_p - m['price']
            shares = int((CAPITAL * RISK_PCT) / dist) if dist > 0 else 0
            if 0 < (shares * m['price']) <= CAPITAL:
                return f"🔻 [放空] 分數:{s_score+20}, 建議空:{shares}股, 守:{stop_p:.1f}"
        return None

def fetch_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period='6mo')
        if len(df) < 60: return None
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_60'] = df['Close'].rolling(60).mean()
        delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        df['TR'] = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(14).mean()
        df['ADX'] = (df['TR'].rolling(14).mean() / df['Close']) * 1000
        l = df.iloc[-1]
        return {'price': l['Close'], 'sma10': l['SMA_10'], 'sma60': l['SMA_60'], 'rsi': l['RSI'], 'adx': l['ADX'], 'vol': l['Volume'], 'avg_vol': df['Volume'].tail(20).mean(), 'high20': df['High'].tail(20).max(), 'low20': df['Low'].tail(20).min(), 'atr': l['ATR']}
    except: return None

def send_line(msg):
    token = os.environ.get("LINE_ACCESS_TOKEN"); uid = os.environ.get("LINE_USER_ID")
    if not token or not uid: return print(msg)
    requests.post("https://api.line.me/v2/bot/message/push", headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, json={"to": uid, "messages": [{"type": "text", "text": msg}]})

def main():
    bot = DualExpert(); results = [f"📊 {datetime.now().strftime('%Y-%m-%d')} 多空雙向報告"]
    with open('my_universe.csv', 'r', encoding='utf-8') as f:
        symbols = [s.strip() for s in f.read().replace('\n', ',').split(',') if s.strip()]
    for s in symbols:
        data = fetch_data(s)
        if data:
            res = bot.analyze(data)
            if res: results.append(f"• {s.split('.')[0]}: {res}")
        time.sleep(0.5)
    if len(results) == 1: results.append("\n💤 今日市場平淡，無建議標的。")
    send_line("\n".join(results))

if __name__ == "__main__":
    main()
