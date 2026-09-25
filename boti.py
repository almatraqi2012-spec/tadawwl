import os
import time
from datetime import datetime
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
    trend_vol_signals = [] 
    momentum_signals = []  
    
    # جلب الوقت الحالي بتنسيق جميل (ساعة:دقيقة - تاريخ)
    current_time = datetime.now().strftime("%Y-%m-%d | %H:%M")
    
    print(f"🔍 جاري فحص السوق عند الساعة {current_time}...")
    
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

                # ==========================================
                # 🟢 الإستراتيجية الأولى: (EMA + Volume)
                # ==========================================
                is_high_volume = current_vol > avg_vol * 1.15
                strat1_long = (cp > cur_ema20) and (cur_ema20 > cur_ema50) and is_high_volume
                strat1_short = (cp < cur_ema20) and (cur_ema20 < cur_ema50) and is_high_volume
                
                if strat1_long or strat1_short:
                    side1 = "LONG 🚀" if strat1_long else "SHORT 📉"
                    tp1 = cp * 1.03 if strat1_long else cp * 0.97
                    sl1 = df.iloc[-10:, 3].min() * 0.99 if strat1_long else df.iloc[-10:, 2].max() * 1.01
                    
                    msg1 = (f"🌊 **توصية (الاتجاه + السيولة)**\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"🪙 العملة: #{symbol}\n"
                            f"⏱ **وقت الرصد:** `{current_time}`\n"
                            f"📊 الإشارة: **{side1}**\n\n"
                            f"📥 الدخول: `{cp}`\n"
                            f"🎯 الهدف: `{round(tp1, 4)}`\n"
                            f"🛑 الوقف: `{round(sl1, 4)}`\n\n"
                            f"• الشروط: EMA + Volume (1.15x)\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"📈 [عرض الشارت المباشر]({chart})")
                    trend_vol_signals.append(msg1)

                # ==========================================
                # 🟣 الإستراتيجية الثانية: (RSI + MACD)
                # ==========================================
                strat2_long = (50 < cur_rsi < 75) and (cur_macd > cur_signal)
                strat2_short = (25 < cur_rsi < 50) and (cur_macd < cur_signal)
                
                if strat2_long or strat2_short:
                    side2 = "LONG 🚀" if strat2_long else "SHORT 📉"
                    tp2 = cp * 1.03 if strat2_long else cp * 0.97
                    sl2 = df.iloc[-10:, 3].min() * 0.99 if strat2_long else df.iloc[-10:, 2].max() * 1.01
                    
                    msg2 = (f"⚡ **توصية (الزخم والدايفرجنس)**\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"🪙 العملة: #{symbol}\n"
                            f"⏱ **وقت الرصد:** `{current_time}`\n"
                            f"📊 الإشارة: **{side2}**\n\n"
                            f"📥 الدخول: `{cp}`\n"
                            f"🎯 الهدف: `{round(tp2, 4)}`\n"
                            f"🛑 الوقف: `{round(sl2, 4)}`\n\n"
                            f"• الشروط: RSI ({round(cur_rsi, 1)}) + MACD Cross\n"
                            f"━━━━━━━━━━━━━━\n"
                            f"📈 [عرض الشارت المباشر]({chart})")
                    momentum_signals.append(msg2)

        except:
            continue
            
    return trend_vol_signals, momentum_signals

def send_results_to_chat(target_chat_id):
    trend_res, momentum_res = scan_market()
    total_sent = 0
    
    if trend_res:
        for res in trend_res[:3]:
            try:
                bot.send_message(target_chat_id, res, parse_mode="Markdown")
                total_sent += 1
            except:
                pass
            
    if momentum_res:
        for res in momentum_res[:3]:
            try:
                bot.send_message(target_chat_id, res, parse_mode="Markdown")
                total_sent += 1
            except:
                pass
            
    if total_sent == 0:
        print("السوق هادئ حالياً، لم يتم إرسال رسائل تلقائية.")

# دالة الفحص التلقائي في الخلفية (كل ساعتين)
def background_scheduler():
    while True:
        time.sleep(15) 
        if CHAT_ID:
            print("⏰ بدء جولة الفحص التلقائي المجدولة...")
            try:
                send_results_to_chat(CHAT_ID)
            except Exception as e:
                print(f"خطأ في الفحص التلقائي: {e}")
        
        time.sleep(7200)

# أوامر البوت اليدوية على تيليجرام
@bot.message_handler(commands=['start', 'scan'])
def handle_commands(message):
    bot.reply_to(message, "⏳ جاري فحص السوق وتحديد أوقات الفرص بدقة...")
    trend_res, momentum_res = scan_market()
    
    total_sent = 0
    if trend_res:
        for res in trend_res[:3]:
            bot.send_message(message.chat.id, res, parse_mode="Markdown")
            total_sent += 1
            
    if momentum_res:
        for res in momentum_res[:3]:
            bot.send_message(message.chat.id, res, parse_mode="Markdown")
            total_sent += 1
            
    if total_sent == 0:
        bot.send_message(message.chat.id, "⚖️ لا توجد توصيات مطابقة للإستراتيجيتين حالياً.")

# خادم ويب لإرضاء منصة Render
app = Flask('')

@app.route('/')
def home():
    return "Bot with Timestamp is active 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    web_thread = Thread(target=run_web)
    web_thread.start()
    
    scheduler_thread = Thread(target=background_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    print("Bot with Timestamps is running successfully on Render...")
    bot.infinity_polling()
