import os
from datetime import datetime
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template_string

app = Flask(__name__)

API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

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

def send_telegram_alert(message):
    if API_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=5)
        except:
            pass

@app.route('/')
def home():
    results = []
    alerts_sent = 0
    current_time = datetime.now().strftime("%Y-%m-%d | %H:%M")
    
    for symbol in TARGET_COINS:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if len(data) < 50:
                    continue
                df = pd.DataFrame(data).astype(float)
                close = df.iloc[:, 4]
                volume = df.iloc[:, 5]
                
                # حساب المؤشرات الأربعة
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
                
                status_list = []

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
                            f"📈 [عرض الشارت]({chart})")
                    send_telegram_alert(msg1)
                    alerts_sent += 1
                    status_list.append(f"إستراتيجية 1: {side1}")

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
                            f"📈 [عرض الشارت]({chart})")
                    send_telegram_alert(msg2)
                    alerts_sent += 1
                    status_list.append(f"إستراتيجية 2: {side2}")

                final_status = " | ".join(status_list) if status_list else "هادئ ⚪"

                results.append({
                    "symbol": symbol,
                    "price": cp,
                    "rsi": round(cur_rsi, 1),
                    "status": final_status
                })
        except:
            continue

    html_template = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>رادار الكريبتو - Vercel</title>
        <style>
            body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
            h1 { text-align: center; color: #38bdf8; }
            p { text-align: center; color: #94a3b8; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e293b; border-radius: 8px; overflow: hidden; }
            th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid #334155; }
            th { background-color: #0284c7; color: white; }
            tr:hover { background-color: #334155; }
            .btn { display: block; width: 220px; margin: 20px auto; padding: 12px; background: #0ea5e9; color: white; text-align: center; text-decoration: none; border-radius: 5px; font-weight: bold; }
            .btn:hover { background: #0284c7; }
        </style>
    </head>
    <body>
        <h1>📊 رادار صفقات الكريبتو (Vercel Cloud)</h1>
        <p>آخر وقت فحص: {{ current_time }} | تم إرسال {{ alerts_sent }} تنبيهات إلى تيليجرام.</p>
        <a href="/" class="btn">🔄 فحص السوق وإرسال التنبيهات</a>
        <table>
            <tr>
                <th>العملة</th>
                <th>السعر الحالي</th>
                <th>مؤشر RSI</th>
                <th>حالة الاستراتيجيات</th>
            </tr>
            {% for item in results %}
            <tr>
                <td><b>{{ item.symbol }}</b></td>
                <td>{{ item.price }}</td>
                <td>{{ item.rsi }}</td>
                <td>{{ item.status }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, results=results, alerts_sent=alerts_sent, current_time=current_time)
