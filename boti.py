import os
import requests
import pandas as pd
import numpy as np
import telebot
from flask import Flask
from threading import Thread

# قراءة توكن البوت من متغيرات البيئة بأمان
API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = telebot.TeleBot(API_TOKEN)

# قائمة العملات المستهدفة بالفحص الشامل
TARGET_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", 
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT",
    "PEPEUSDT", "SHIBUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT"
]

def calculate_rsi(series, period=14):
    """حساب مؤشر القوة النسبية RSI يدوياً بدقة"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def scan_market():
    signals = []
    print("🔍 جاري فحص السوق عبر معادلة المحترفين (EMA + الزخم + السيولة)...")
    
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
                
                # 1. حساب مؤشرات الاتجاه (EMA 20 & EMA 50)
                ema20 = close.ewm(span=20).mean()
                ema50 = close.ewm(span=50).mean()
                
                # 2. حساب الزخم (RSI 14) و (MACD)
                rsi = calculate_rsi(close, 14)
                
                exp1 = close.ewm(span=12, adjust=False).mean()
                exp2 = close.ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal_line = macd.ewm(span=9, adjust=False).mean()
                
                # القيم الحالية لآخر شمعة مغلقة
                cp = close.iloc[-1]
                cur_ema20 = ema20.iloc[-1]
                cur_ema50 = ema50.iloc[-1]
                cur_rsi = rsi.iloc[-1]
                cur_macd = macd.iloc[-1]
                cur_signal = signal_line.iloc[-1]
                
                # 3. حساب السيولة (الحجم الحالي مقارنة بمتوسط 20 شمعة)
                avg_vol = volume.rolling(20).mean().iloc[-1]
                current_vol = volume.iloc[-1]
                
                # شروط التصفية الصارمة (فلترة الفرص القوية جداً)
                is_high_volume = current_vol > avg_vol * 1.3
                
                # شروط الشراء (LONG): الاتجاه صاعد + زخم ايجابي (RSI بين 50 و 75 و MACD فوق خط الإشارة)
                is_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50) and (50 < cur_rsi < 75) and (cur_macd > cur_signal)
                
                # شروط البيع (SHORT): الاتجاه هابط + زخم سلبي (RSI بين 25 و 50 و MACD تحت خط الإشارة)
                is_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50) and (25 < cur_rsi < 50) and (cur_macd < cur_signal)
                
                if is_high_volume and (is_long or is_short):
                    side = "LONG 🚀" if is_long else "SHORT 📉"
                    vol_status = "انفجار سيولة قوي 🔥"
                    
                    tp = cp * 1.035 if is_long else cp * 0.965
                    sl = df.iloc[-10:, 3].min() * 0.985 if is_long else df.iloc[-10:, 2].max() * 1.015
                    
                    chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"
                    
                    msg = (f"🏛 **تقرير رادار الاحترافي (مؤشرات كاملة)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"📊 الإشارة: **{side}**\n\n"
                           f"📥 الدخول: `{cp}`\n"
                           f"🎯 الهدف: `{round(tp, 4)}`\n"
                           f"🛑 الوقف: `{round(sl, 4)}`\n\n"
                           f"📈 مؤشرات الزخم:\n"
                           f"• RSI: `{round(cur_rsi, 1)}`\n"
                           f"• الحالة: {vol_status}\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [عرض الشارت المباشر]({chart})")
                    
                    signals.append(msg)
        except Exception as e:
            continue
            
    return signals

@bot.message_handler(commands=['scan', 'start'])
def send_welcome(message):
    bot.reply_to(message, "⚙️ جاري تحليل السوق باستخدام (EMA + RSI + MACD + Volume)... يرجى الانتظار لحظات.")
    signals = scan_market()
    
    if not signals:
        bot.send_message(message.chat.id, "⚖️ لا توجد فرص تطابق المعايير الصارمة للمؤشرات حالياً. السوق يتطلب صبراً.")
    else:
        for sig in signals[:5]:
            bot.send_message(message.chat.id, sig, parse_mode="Markdown")

# إبقاء السكربت نشطاً بخادم ويب خفيف
app = Flask('')

@app.route('/')
def home():
    return "Pro Crypto Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    t = Thread(target=run_web)
    t.start()
    
    print("Bot is polling with full indicators...")
    bot.infinity_polling()
