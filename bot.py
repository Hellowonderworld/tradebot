import os, yfinance as yf, pandas as pd, requests, time, csv
from datetime import datetime

# ==========================================
# 專家系統參數設定
# ==========================================
CAPITAL = 16000        # 每月投入本金 (NTD)
RISK_PCT = 0.05       # 單筆交易最大虧損比例 (5%)

class TradingExpert:
    def analyze(self, m):
        score = 0
        # 核心規則 (Core Rules)
        if m['sma10'] > m['sma60']: score += 30      # 均線多頭
        if 40 <= m['rsi'] <= 65: score += 20         # RSI 健康區間
        if m['vol'] > m['avg_vol'] * 1.3: score += 20 # 成交量異常放大
        if m['price'] > m['high20']: score += 20      # 突破近期高點
        
        # 趨勢過濾 (ADX < 18 代表橫盤盤整，不建議進場)
        if m['adx'] < 18: return None 
        
        # 門檻判定與部位計算
        if score >= 60:
            risk_amt = CAPITAL * RISK_PCT
            # 計算停損距離 (目前價格與 20 日最低點的差距)
            dist = m['price'] - m['low20']
            dist = dist if dist > 0 else m['price'] * 0.03 # 預設最小 3% 空間
            
            shares = int(risk_amt / dist)
            cost = shares * m['price']
            
            if shares > 0 and cost <= CAPITAL:
                return f"✅ [訊號] 分數:{score}, 建議買:{shares}股, 成本約:{cost:.0f}"
            elif shares > 0:
                return f"⚠️ [預算不足] 分數:{score}, 需{cost:.0f}元"
        return None

def fetch_data(symbol):
    """抓取 Yahoo Finance 資料並計算指標"""
    try:
        df = yf.Ticker(symbol).history(period='6mo')
        if len(df) < 60: return None
        
        # 計算技術指標 (不使用外部套件，確保穩定)
        df['SMA_10'] = df['Close'].rolling(window=10).mean()
        df['SMA_60'] = df['Close'].rolling(window=60).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        df['TR'] = pd.concat([df['High'] - df['Low'], 
                             (df['High'] - df['Close'].shift()).abs(), 
                             (df['Low'] - df['Close'].shift()).abs()], axis=1).max(axis=1)
        df['ADX_14'] = (df['TR'].rolling(window=14).mean() / df['Close']) * 1000
        
        l = df.iloc[-1]
        return {
            'price': l['Close'], 'sma10': l['SMA_10'], 'sma60': l['SMA_60'],
            'rsi': l['RSI_14'], 'adx': l['ADX_14'], 'vol': l['Volume'],
            'avg_vol': df['Volume'].tail(20).mean(),
            'high20': df['High'].tail(20).max(), 'low20': df['Low'].tail(20).min()
        }
    except:
        return None

def send_line(msg):
    """透過 Messaging API 發送 Push Message"""
    token = os.environ.get("LINE_ACCESS_TOKEN")
    uid = os.environ.get("LINE_USER_ID")
    if not token or not uid: 
        print("未設定環境變數，報告如下：\n", msg)
        return
    
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    payload = {"to": uid, "messages": [{"type": "text", "text": msg}]}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print("✅ LINE 訊息發送成功！")
    else:
        print(f"❌ LINE 發送失敗: {response.text}")

def main():
    bot = TradingExpert()
    report_date = datetime.now().strftime('%Y-%m-%d')
    results = [f"📊 {report_date} 量化掃描報告"]
    
    # 讀取觀察名單
    symbols = []
    try:
        with open('my_universe.csv', 'r', encoding='utf-8') as f:
            content = f.read().replace('\n', ',')
            symbols = [s.strip() for s in content.split(',') if s.strip()]
    except:
        symbols = ["2330.TW", "2317.TW", "2454.TW"] # 預設保底清單

    print(f"開始掃描 {len(symbols)} 檔標的...")
    for s in symbols:
        data = fetch_data(s)
        if data:
            res = bot.analyze(data)
            if res: 
                results.append(f"• {s.split('.')[0]}: {res}")
        time.sleep(0.5) # 稍微暫停避免被 Yahoo 鎖 IP

    # 最終訊息組合：若無推薦，則顯示「今日無推薦股票」
    if len(results) == 1:
        results.append("\n💤 今日無符合條件之推薦股票。")
        results.append("系統運作正常，請繼續保持耐心與紀律。")

    final_msg = "\n".join(results)
    send_line(final_report) # 或者是 final_msg

if __name__ == "__main__":
    # 注意：這裡把變數名稱統一為 final_msg 以免報錯
    def main_fixed():
        bot = TradingExpert()
        report_date = datetime.now().strftime('%Y-%m-%d')
        results = [f"📊 {report_date} 量化掃描報告"]
        
        symbols = []
        try:
            with open('my_universe.csv', 'r', encoding='utf-8') as f:
                content = f.read().replace('\n', ',')
                symbols = [s.strip() for s in content.split(',') if s.strip()]
        except:
            symbols = ["2330.TW", "2317.TW", "2454.TW"]

        for s in symbols:
            data = fetch_data(s)
            if data:
                res = bot.analyze(data)
                if res: results.append(f"• {s.split('.')[0]}: {res}")
            time.sleep(0.5)

        if len(results) == 1:
            results.append("\n💤 今日無符合條件之推薦股票。")
            results.append("系統運作正常，請繼續保持耐心與紀律。")

        send_line("\n".join(results))
    
    main_fixed()
