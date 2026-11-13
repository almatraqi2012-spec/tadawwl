import os
import time
from datetime import datetime
import requests
import pandas as pd
import numpy as np

# === [ إعدادات VIP - شركة سهم القابضة ] ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# ========================================

TARGET_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", 
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "SUIUSDT",
    "PEPEUSDT", "SHIBUSDT", "RENDERUSDT", "FETUSDT", "INJUSDT",
    "UNIUSDT", "ATOMUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", 
    "LTCUSDT", "BCHUSDT", "ICPUSDT", "FILUSDT", "TONUSDT", 
    "TIAUSDT", "SEIUSDT", "AAVEUSDT", "JUPUSDT", "WIFUSDT"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def format_price(price):
    if price < 0.0001:
        return f"{price:.8f}"
    elif price < 1:
        return f"{price:.4f}"
    else:
        return f"{price:.2f}"

def send_confirmed_signal(symbol, price, pattern_name, side, tp1, tp2, sl):
    clean_sym = symbol.replace("USDT", "")
    emoji = "🚀 (صعود - LONG)" if side == "LONG" else "📉 (نزول - SHORT)"
    current_time = datetime.now().strftime("%Y-%m-%d | %H:%M:%S")
    tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_sym}USDT"

    msg = (
        f"🏛 *شركة سهم القابضة للاستثمار*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 *تنبيه نموذج كلاسيكي (من الشارت)*\n\n"
        f"🪙 *العملة:* #{clean_sym}\n"
        f"📐 *النموذج:* `{pattern_name}`\n"
        f"📊 *الاتجاه:* {emoji}\n"
        f"⏱ *الوقت:* `{current_time}`\n\n"
        f"📥 *سعر الدخول:* `{format_price(price)}`\n\n"
        f"🎯 *الأهداف:*\n"
        f"1️⃣ *الهدف الأول (TP1):* `{format_price(tp1)}`\n"
        f"2️⃣ *الهدف الثاني (TP2):* `{format_price(tp2)}`\n\n"
        f"🛡️ *وقف الخسارة (SL):* `{format_price(sl)}`\n\n"
        f"🔗 *[فحص الشارت المباشر عبر TradingView]({tv_link})*\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            print(f"✅ تم إرسال تنبيه نموذج {pattern_name} لـ {symbol}")
        except Exception as e:
            print(f"❌ خطأ في إرسال التليجرام: {e}")

def detect_all_patterns(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list) or len(data) < 40:
                return None
            
            df = pd.DataFrame(data).astype(float)
            highs = df.iloc[:, 2].tail(35)
            lows = df.iloc[:, 3].tail(35)
            close = df.iloc[:, 4].tail(30)
            cp = close.iloc[-1]
            
            # حساب الانحدار للقمم والقيعان لاكتشاف الأشكال الهندسية بدقة
            low_slope = np.polyfit(np.arange(35), lows.values, 1)[0]
            high_slope = np.polyfit(np.arange(35), highs.values, 1)[0]
            
            # 1. الأوتاد الصاعدة والنازلة (Rising & Falling Wedges) والأعلام (Flags)
            if low_slope > 0 and high_slope > 0 and high_slope < low_slope:
                # الوتد الصاعد الانعكاسي للنزول (Rising Wedge)
                return "Rising Wedge (إشارة نزول)", "SHORT", cp * 0.975, cp * 0.95, cp * 1.015
            elif low_slope < 0 and high_slope < 0 and abs(low_slope) > abs(high_slope):
                # الوتد الهابط للصعود (Falling Wedge)[cite: 1]
                return "Falling Wedge (إشارة صعود)", "LONG", cp * 1.025, cp * 1.05, cp * 0.985
                
            # 2. المثلثات (Ascending & Descending Triangles)[cite: 1]
            elif low_slope > 0 and highs.std() / cp < 0.02 and cp >= highs.max() * 0.985:
                return "Ascending Triangle (اختراق صاعد)", "LONG", cp * 1.025, cp * 1.05, cp * 0.985
            elif high_slope < 0 and lows.std() / cp < 0.02 and cp <= lows.min() * 1.015:
                return "Descending Triangle (كسر هابط)", "SHORT", cp * 0.975, cp * 0.95, cp * 1.015
                
            # 3. القمم والقيعان المزدوجة (Double Top & Double Bottom)[cite: 1]
            elif abs(highs.iloc[-1] - highs.iloc[-15]) / cp < 0.005 and cp < highs.mean() * 0.99:
                return "Double Top (قمة مزدوجة - انعكاس هابط)", "SHORT", cp * 0.97, cp * 0.94, cp * 1.015
            elif abs(lows.iloc[-1] - lows.iloc[-15]) / cp < 0.005 and cp > lows.mean() * 1.01:
                return "Double Bottom (قاع مزدوج - انعكاس صاعد)", "LONG", cp * 1.03, cp * 1.06, cp * 0.985
                
    except Exception as e:
        pass
    return None

def main():
    print(f"📡 رادار النماذج المتكاملة لشركة سهم القابضة يبدأ فحص العملات...")
    signals_found = 0
    
    for symbol in TARGET_COINS:
        print(f"🔍 فحص الشارت لـ {symbol}...")
        res = detect_all_patterns(symbol)
        if res:
            pattern_name, side, tp1, tp2, sl = res
            price = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", headers=HEADERS).json()['price'])
            send_confirmed_signal(symbol, price, pattern_name, side, tp1, tp2, sl)
            signals_found += 1
        time.sleep(0.5)
            
    print(f"✨ انتهت دورة الفحص. الصفقات المكتشفة: {signals_found}")

if __name__ == "__main__":
    main()
