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
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            r = requests.post(url, json=payload, timeout=5)
            return r.status_code == 200
        except:
            return False
    return False

def main():
    current_time = datetime.now().strftime("%Y-%m-%d | %H:%M")
    print(f"🚀 بدء فحص المؤشرات المستقلة لـ {len(TARGET_COINS)} عملة...")
    
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
                
                # حساب المؤشرات
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

                # ----------------------------------------------------
                # 1️⃣ مؤشر المتوسطات المتحركة (EMA) وحده
                # ----------------------------------------------------
                ema_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50)
                ema_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50)
                if ema_long or ema_short:
                    side = "LONG 🚀 (شراء)" if ema_long else "SHORT 📉 (بيع)"
                    msg = (f"📈 **تنبيه مؤشر (EMA)**\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الإشارة: **{side}**\n"
                           f"📥 السعر: `{cp}`\n"
                           f"📈 [رابط الشارت]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 2️⃣ مؤشر السيولة (Volume) وحده
                # ----------------------------------------------------
                is_high_volume = current_vol > avg_vol * 1.15
                if is_high_volume:
                    msg = (f"🌊 **تنبيه مؤشر السيولة (Volume)**\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الحالة: حجم تداول عالي يتجاوز المتوسط!\n"
                           f"📥 السعر: `{cp}`\n"
                           f"📈 [رابط الشارت]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 3️⃣ مؤشر القوة النسبية (RSI) وحده
                # ----------------------------------------------------
                rsi_oversold = cur_rsi < 30
                rsi_overbought = cur_rsi > 70
                if rsi_oversold or rsi_overbought:
                    side = "LONG 🚀 (تشبع بيع - ارتداد)" if rsi_oversold else "SHORT 📉 (تشبع شراء)"
                    msg = (f"⚡ **تنبيه مؤشر (RSI)**\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 قيمة RSI: `{round(cur_rsi, 1)}`\n"
                           f" الإشارة: **{side}**\n"
                           f"📥 السعر: `{cp}`\n"
                           f"📈 [رابط الشارت]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 4️⃣ مؤشر الماكد (MACD) وحده
                # ----------------------------------------------------
                macd_bullish = cur_macd > cur_signal and cur_macd < 0
                macd_bearish = cur_macd < cur_signal and cur_macd > 0
                if macd_bullish or macd_bearish:
                    side = "LONG 🚀 (تقاطع إيجابي MACD)" if macd_bullish else "SHORT 📉 (تقاطع سلبي MACD)"
                    msg = (f"🎯 **تنبيه مؤشر (MACD)**\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الإشارة: **{side}**\n"
                           f"📥 السعر: `{cp}`\n"
                           f"📈 [رابط الشارت]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

        except Exception as e:
            continue
            
    print(f"✨ اكتمل فحص جميع المؤشرات. إجمالي التنبيهات: {alerts_sent}")

if __name__ == "__main__":
    main()
