import os
import requests
import pandas as pd
import numpy as np
import telebot
from flask import Flask
from threading import Thread

# قراءة البيانات من متغيرات البيئة بأمان
API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
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

def scan_market():
    signals = []
    print("🔍 جاري فحص السوق بناءً على طلبك...")
    
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
                
                # شروط مرنة لضمان ظهور نتائج عند الفحص اليدوي
                is_high_volume = current_vol > avg_vol * 1.12
                is_long = (cp > cur_ema20) and (40 < cur_rsi < 85) and (cur_macd > cur_signal)
                is_short = (cp < cur_ema20) and (15 < cur_rsi < 60) and (cur_macd < cur_signal)
                
                if is_high_volume and (is_long or is_short):
                    side = "LONG 🚀" if is_long else "SHORT 📉"
                    tp = cp * 1.03 if is_long else cp * 0.97
                    sl = df.iloc[-10:, 3].min() * 0.99 if is_long else df.iloc[-10:, 2].max() * 1.01
                    chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
                    
                    msg = (f"🏛 **تقرير رادار المنصة (مباشر)**\n"
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
            
    return signals

# أوامر البوت على تيليجرام
@bot.message_handler(commands=['start', 'scan'])
def handle_commands(message):
    bot.reply_to(message, "⏳ جاري فحص العملات الآن، انتظر لحظات...")
    results = scan_market()
    if not results:
        bot.send_message(message.chat.id, "⚖️ لا توجد فرص قوية مطابقة للمعايير في هذه اللحظة، حاول مرة أخرى لاحقاً.")
    else:
        for res in results[:5]:
            bot.send_message(message.chat.id, res, parse_mode="Markdown")

# خادم ويب خفيف لإرضاء منصة Render ومنع انقطاع السيرفر
app = Flask('')

@app.route('/')
def home():
    print("Health check ping received!")
    return "Bot is alive and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # تشغيل خادم الويب في الخلفية
    web_thread = Thread(target=run_web)
    web_thread.start()
    
    print("Bot is polling interactively on Render...")
    bot.infinity_polling()
