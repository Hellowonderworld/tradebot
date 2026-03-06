import os, yfinance as yf, pandas as pd, requests, time, csv
from datetime import datetime

# 專家系統參數
CAPITAL = 2500        # 本金
RISK_PCT = 0.05       # 單筆風險 5%

class TradingExpert:
    def analyze(self, m):
        score = 0
        # 規則檢查
        if m['sma10'] > m['sma60']: score += 30
        if 40 <= m['rsi'] <= 65: score += 20
        if m['vol'] > m['avg_vol'] * 1.3: score += 20
        if m['price'] > m['high20']: score += 20
        
        if m['adx'] < 18: return None # 稍微放寬 ADX 門檻
        
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
        
        # --- 手動計算技術指標 (替代 pandas_ta) ---
        # 1. 均線 SMA
        df['SMA_10'] = df['Close'].rolling(window=10).mean()
        df['SMA_60'] = df['Close'].rolling(window=60).mean()
        
        # 2. RSI (相對強弱指標)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # 3. 簡單版 ADX (趨勢強度) - 簡化計算確保穩定
        df['TR'] = pd.concat([df['High'] - df['Low'], 
                             (df['High'] - df['Close'].shift()).abs(), 
                             (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ADX_14'] = (df['TR'].rolling(window=14).mean() / df['Close']) * 1000 # 趨勢強度係數
        
        # --- 數據打包 ---
        l = df.iloc[-1]
        return {
            'price': l['Close'], 'sma10': l['SMA_10'], 'sma60': l['SMA_60'],
            'rsi': l['RSI_14'], 'adx': l['ADX_14'], 'vol': l['Volume'],
            'avg_vol': df['Volume'].tail(20).mean(),
            'high20': df['High'].tail(20).max(), 'low20': df['Low'].tail(20).min()
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

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
    
    # 讀取 CSV
    symbols = []
    try:
        with open('my_universe.csv', 'r', encoding='utf-8') as f:
            content = f.read().replace('\n', ',')
            symbols = [s.strip() for s in content.split(',') if s.strip()]
    except:
        symbols = ["2330.TW", "2317.TW"] # 保底

    for s in symbols:
        data = fetch_data(s)
        if data:
            res = bot.analyze(data)
            if res: results.append(f"• {s.split('.')[0]}: {res}")
        time.sleep(0.6)

    send_line("\n".join(results) if len(results) > 1 else "今日無符合條件標的。")

if __name__ == "__main__":
    main()
