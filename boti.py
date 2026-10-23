import os
from datetime import datetime
import requests
import pandas as pd
import numpy as np

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TARGET_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", 
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT",
    "PEPEUSDT", "SHIBUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT",
    "MATICUSDT", "UNIUSDT", "ATOMUSDT", "APTUSDT", "ARBUSDT",
    "OPUSDT", "LTCUSDT", "BCHUSDT", "ICPUSDT", "FILUSDT",
    "TONUSDT", "TIAUSDT", "SEIUSDT", "SAGAUSDT", "STRKUSDT",
    "MANTAUSDT", "PENDLEUSDT", "RUNEUSDT", "GRTUSDT", "AAVEUSDT",
    "MKRUSDT", "SNXUSDT", "CRVUSDT", "COMPUSDT", "JUPUSDT",
    "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "BOMEUSDT", "NOTUSDT", "DOGSUSDT"
]

TARGET_COINS = list(set(TARGET_COINS))

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def send_telegram_alert(message):
    if API_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(url, json=payload, timeout=5)
            return r.status_code == 200
        except:
            return False
    return False

def main():
    current_time = datetime.now().strftime("%Y-%m-%d | %H:%M")
    print(f"🚀 بدء فحص السوق لـ {len(TARGET_COINS)} عملة...")
    
    alerts_sent = 0
    
    for symbol in TARGET_COINS:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) < 50:
                    continue
                df = pd.DataFrame(data).astype(float)
                close = df.iloc[:, 4]
                volume = df.iloc[:, 5]
                
                # حساب المؤشرات الفنية
                ema20 = close.ewm(span=20).mean()
                ema50 = close.ewm(span=50).mean()
                rsi = calculate_rsi(close, 14)
                
                exp1 = close.ewm(span=12, adjust=False).mean()
                exp2 = close.ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                cp = close.iloc[-1]
                cur_ema20 = ema20.iloc[-1]
                cur_ema50 = ema50.iloc[-1]
                cur_rsi = rsi.iloc[-1]
                cur_macd = macd.iloc[-1]
                cur_signal = signal_line.iloc[-1]
                
                avg_vol = volume.rolling(20).mean().iloc[-1]
                current_vol = volume.iloc[-1]
                chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"

                print(f"Flipping {symbol} -> Price: {cp}, RSI: {round(cur_rsi, 1)}")

                # شروط استراتيجية الاتجاه والسيولة
                is_active_volume = current_vol > avg_vol * 1.05
                strat_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50) and is_active_volume
                strat_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50) and is_active_volume
                
                if strat_long or strat_short:
                    side = "LONG 🚀 (شراء)" if strat_long else "SHORT 📉 (بيع)"
                    tp = cp * 1.025 if strat_long else cp * 0.975
                    sl = cp * 0.985 if strat_long else cp * 1.015
                    
                    msg = (f"🔥 **فرصة تداول مرصودة**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الاتجاه: **{side}**\n\n"
                           f"📥 سعر الدخول: `{cp}`\n"
                           f"🎯 الهدف: `{round(tp, 4)}`\n"
                           f"🛑 وقف الخسارة: `{round(sl, 4)}`\n\n"
                           f"• مؤشر RSI: `{round(cur_rsi, 1)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    
                    if send_telegram_alert(msg):
                        print(f"✅ تم إرسال تنبيه ناجح للعملة: {symbol}")
                        alerts_sent += 1
        except Exception as e:
            print(f"خطأ في تحليل العملة {symbol}: {e}")
            continue
            
    print(f"✨ اكتملت دورة الفحص. إجمالي التنبيهات المرسلة: {alerts_sent}")

if __name__ == "__main__":
    main()
