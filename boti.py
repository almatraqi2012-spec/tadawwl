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
    print(f"🚀 بدء تحليل توقع الشمعات (30 شمعة) لـ {len(TARGET_COINS)} عملة...")
    
    alerts_sent = 0
    
    for symbol in TARGET_COINS:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) < 35:
                    continue
                df = pd.DataFrame(data).astype(float)
                close = df.iloc[:, 4]
                volume = df.iloc[:, 5]
                
                # تركيز التحليل على آخر 30 شمعة
                recent_close = close.tail(30)
                recent_volume = volume.tail(30)
                
                ema20 = recent_close.ewm(span=20).mean()
                ema50 = recent_close.ewm(span=15).mean()
                rsi = calculate_rsi(recent_close, 14)
                
                exp1 = recent_close.ewm(span=12, adjust=False).mean()
                exp2 = recent_close.ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                cp = recent_close.iloc[-1]
                cur_ema20 = ema20.iloc[-1]
                cur_ema50 = ema50.iloc[-1]
                cur_rsi = rsi.iloc[-1]
                cur_macd = macd.iloc[-1]
                cur_signal = signal_line.iloc[-1]
                
                avg_vol = recent_volume.rolling(10).mean().iloc[-1]
                current_vol = recent_volume.iloc[-1]
                chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"

                # ----------------------------------------------------
                # 1️⃣ توقع الشمعات عبر مؤشر (EMA)
                # ----------------------------------------------------
                ema_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50)
                ema_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50)
                if ema_long or ema_short:
                    side = "LONG 🚀 (توقع صعود الشمعات)" if ema_long else "SHORT 📉 (توقع هبوط الشمعات)"
                    tp = cp * 1.025 if ema_long else cp * 0.975
                    sl = cp * 0.985 if ema_long else cp * 1.015
                    msg = (f"📈 **تحليل الشمعات (مؤشر الاتجاه EMA)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 حركة آخر 30 شمعة: **{side}**\n\n"
                           f"📥 سعر الدخول: `{cp}`\n"
                           f"🎯 الهدف (TP): `{round(tp, 4)}`\n"
                           f"🛑 وقف الخسارة (SL): `{round(sl, 4)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 2️⃣ توقع الشمعات عبر (السيولة Volume)
                # ----------------------------------------------------
                is_high_volume = current_vol > avg_vol * 1.15
                if is_high_volume:
                    tp = cp * 1.025
                    sl = cp * 0.985
                    msg = (f"🌊 **تحليل الشمعات (مؤشر السيولة)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الحالة: حجم الشمعة الحالية يتجاوز متوسط الـ 30 شمعة\n\n"
                           f"📥 سعر الدخول: `{cp}`\n"
                           f"🎯 الهدف (TP): `{round(tp, 4)}`\n"
                           f"🛑 وقف الخسارة (SL): `{round(sl, 4)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 3️⃣ توقع الشمعات عبر (RSI)
                # ----------------------------------------------------
                rsi_oversold = cur_rsi < 30
                rsi_overbought = cur_rsi > 70
                if rsi_oversold or rsi_overbought:
                    side = "LONG 🚀 (تشبع بيع - ارتداد شمعي صاعد)" if rsi_oversold else "SHORT 📉 (تشبع شراء - هبوط شمعي)"
                    tp = cp * 1.025 if rsi_oversold else cp * 0.975
                    sl = cp * 0.985 if rsi_oversold else cp * 1.015
                    msg = (f"⚡ **تحليل الشمعات (مؤشر RSI)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 قيمة RSI (للـ 30 شمعة): `{round(cur_rsi, 1)}`\n"
                           f" الإشارة: **{side}**\n\n"
                           f"📥 سعر الدخول: `{cp}`\n"
                           f"🎯 الهدف (TP): `{round(tp, 4)}`\n"
                           f"🛑 وقف الخسارة (SL): `{round(sl, 4)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                # ----------------------------------------------------
                # 4️⃣ توقع الشمعات عبر (MACD)
                # ----------------------------------------------------
                macd_bullish = cur_macd > cur_signal and cur_macd < 0
                macd_bearish = cur_macd < cur_signal and cur_macd > 0
                if macd_bullish or macd_bearish:
                    side = "LONG 🚀 (تقاطع إيجابي MACD)" if macd_bullish else "SHORT 📉 (تقاطع سلبي MACD)"
                    tp = cp * 1.025 if macd_bullish else cp * 0.975
                    sl = cp * 0.985 if macd_bullish else cp * 1.015
                    msg = (f"🎯 **تحليل الشمعات (مؤشر MACD)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الإشارة: **{side}**\n\n"
                           f"📥 سعر الدخول: `{cp}`\n"
                           f"🎯 الهدف (TP): `{round(tp, 4)}`\n"
                           f"🛑 وقف الخسارة (SL): `{round(sl, 4)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    if send_telegram_alert(msg):
                        alerts_sent += 1

        except Exception as e:
            continue
            
    print(f"✨ اكتمل تحليل الشمعات. إجمالي التنبيهات: {alerts_sent}")

if __name__ == "__main__":
    main()
