import os
import requests
import pandas as pd
import numpy as np
import telebot

# قراءة توكن البوت
API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

TARGET_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", 
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT",
    "PEPEUSDT", "SHIBUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT"
]

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_and_send():
    print("🔍 بدء فحص السوق وإرسال التنبيهات...")
    signals = []
    
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
                
                is_high_volume = current_vol > avg_vol * 1.3
                is_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50) and (50 < cur_rsi < 75) and (cur_macd > cur_signal)
                is_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50) and (25 < cur_rsi < 50) and (cur_macd < cur_signal)
                
                if is_high_volume and (is_long or is_short):
                    side = "LONG 🚀" if is_long else "SHORT 📉"
                    tp = cp * 1.035 if is_long else cp * 0.965
                    sl = df.iloc[-10:, 3].min() * 0.985 if is_long else df.iloc[-10:, 2].max() * 1.015
                    chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
                    
                    msg = (f"🏛 **تقرير رادار الاحترافي**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"📊 الإشارة: **{side}**\n\n"
                           f"📥 الدخول: `{cp}`\n"
                           f"🎯 الهدف: `{round(tp, 4)}`\n"
                           f"🛑 الوقف: `{round(sl, 4)}`\n\n"
                           f"• RSI: `{round(cur_rsi, 1)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [عرض الشارت]({chart})")
                    signals.append(msg)
        except:
            continue
            
    # إرسال النتائج عبر تيليجرام دفعة واحدة
    CHAT_ID = os.getenv("CHAT_ID") # أو ضع ايديك مباشرة هنا
    if signals and CHAT_ID:
        for sig in signals[:5]:
            requests.post(
                f"https://api.telegram.org/bot{API_TOKEN}/sendMessage",
                json={"chat_id": CHAT_ID, "text": sig, "parse_mode": "Markdown"}
            )
    print("تم الانتهاء وإرسال التقارير بنجاح.")

if __name__ == "__main__":
    scan_and_send()
