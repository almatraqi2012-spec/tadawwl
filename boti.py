import requests
import pandas as pd
import numpy as np
import os

# === [ إعدادات VIP - شركة سهم القابضة ] ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# ========================================

# قائمة العملات القوية الكبرى التي يتداول عليها الحيتان مباشرة لتجنب حظر الـ API العام
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

def send_confirmed_signal(symbol, price, model_type, tp1, tp2, sl):
    clean_sym = symbol.replace("USDT", "")
    emoji = "🚀" if "صاعد" in model_type else "📉"
    tv_link = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_sym}USDT"

    msg = (
        f"🏛 *شركة سهم القابضة للاستثمار*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{emoji} *توصية هندسية مؤكدة (نماذج حقيقية)*\n\n"
        f"💰 *العملة:* #{clean_sym}\n"
        f"📐 *الحالة:* {model_type}\n\n"
        f"📥 *سعر الدخول:* `{price}`\n\n"
        f"🎯 *الأهداف (VIP):*\n"
        f"1️⃣ *هدف أول:* `{tp1}`\n"
        f"2️⃣ *هدف ثاني:* `{tp2}`\n\n"
        f"🛡️ *وقف الخسارة:* `{sl}`\n\n"
        f"🔗 *[فحص الشارت عبر TradingView]({tv_link})*\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
            print(f"✅ تم إرسال توصية نموذج حقيقي لـ {symbol}")
        except Exception as e:
            print(f"❌ خطأ في إرسال التليجرام: {e}")

def analyze_triangle_patterns(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=40"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if not isinstance(data, list) or len(data) < 35:
                return None
            
            df = pd.DataFrame(data).astype(float)
            highs = df.iloc[:, 2].tail(30)
            lows = df.iloc[:, 3].tail(30)
            close = df.iloc[:, 4].tail(30)
            
            cp = close.iloc[-1]
            
            low_slope = np.polyfit(np.arange(30), lows.values, 1)[0]
            high_std = highs.std()
            is_ascending_triangle = (low_slope > 0) and (high_std / cp < 0.015) and (cp >= highs.max() * 0.99)
            
            high_slope = np.polyfit(np.arange(30), highs.values, 1)[0]
            low_std = lows.std()
            is_descending_triangle = (high_slope < 0) and (low_std / cp < 0.015) and (cp <= lows.min() * 1.01)
            
            if is_ascending_triangle:
                tp1 = round(cp * 1.025, 4 if cp < 1 else 2)
                tp2 = round(cp * 1.05, 4 if cp < 1 else 2)
                sl = round(cp * 0.985, 4 if cp < 1 else 2)
                return "اختراق مثلث صاعد حقيقي ✅", tp1, tp2, sl, cp
                
            elif is_descending_triangle:
                tp1 = round(cp * 0.975, 4 if cp < 1 else 2)
                tp2 = round(cp * 0.95, 4 if cp < 1 else 2)
                sl = round(cp * 1.015, 4 if cp < 1 else 2)
                return "كسر مثلث نازل حقيقي 📉", tp1, tp2, sl, cp
                
    except Exception as e:
        pass
    return None

def main():
    print(f"📡 رادار شركة سهم القابضة يبدأ فحص {len(TARGET_COINS)} عملة رئيسية...")
    
    signals_found = 0
    for symbol in TARGET_COINS:
        result = analyze_triangle_patterns(symbol)
        if result:
            model_type, tp1, tp2, sl, price = result
            send_confirmed_signal(symbol, price, model_type, tp1, tp2, sl)
            signals_found += 1
            
    print(f"✨ انتهت دورة الفحص بنجاح. الصفقات المكتشفة: {signals_found}")

if __name__ == "__main__":
    main()
