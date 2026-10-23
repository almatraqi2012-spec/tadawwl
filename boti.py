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

def format_price(price):
    """تنسيق دقيق وحقيقي للأعراب والعملات بمختلف أحجامها"""
    if price < 0.0001:
        return f"{price:.8f}"
    elif price < 1:
        return f"{price:.4f}"
    else:
        return f"{price:.2f}"

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    """حساب مؤشر التذبذب الحقيقي (ATR) لحماية الصفقة وتحديد أهداف واقعية"""
    high = df.iloc[:, 2]
    low = df.iloc[:, 3]
    close = df.iloc[:, 4]
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

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
    print(f"💼 بدء التحليل الاحترافي الحقيقي (Confluence + ATR) لـ {len(TARGET_COINS)} عملة...")
    
    alerts_sent = 0
    
    for symbol in TARGET_COINS:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=60"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if len(data) < 40:
                    continue
                df = pd.DataFrame(data).astype(float)
                close = df.iloc[:, 4]
                volume = df.iloc[:, 5]
                
                # حساب المؤشرات الاحترافية
                ema20 = close.ewm(span=20).mean()
                ema50 = close.ewm(span=50).mean()
                rsi = calculate_rsi(close, 14)
                atr = calculate_atr(df, 14)
                
                cp = close.iloc[-1]
                cur_ema20 = ema20.iloc[-1]
                cur_ema50 = ema50.iloc[-1]
                cur_rsi = rsi.iloc[-1]
                cur_atr = atr.iloc[-1]
                
                avg_vol = volume.rolling(20).mean().iloc[-1]
                current_vol = volume.iloc[-1]
                chart = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}"

                # التحقق من صحة بيانات ATR لتجنب أي أخطاء
                if np.isnan(cur_atr) or cur_atr <= 0:
                    continue

                # ----------------------------------------------------
                # إستراتيجية التقاء المؤشرات الحقيقية (Confluence Strategy)
                # ----------------------------------------------------
                
                # شرط الشراء (LONG الاحترافي): الاتجاه صاعد + سيولة مرتفعة + RSI غير مشبع شراء
                is_trend_up = (cp > cur_ema20) and (cur_ema20 > cur_ema50)
                is_volume_high = current_vol > (avg_vol * 1.2) # سيولة أعلى بـ 20% من المتوسط
                is_rsi_safe_long = (cur_rsi > 45) and (cur_rsi < 68)

                # شرط البيع (SHORT الاحترافي): الاتجاه هابط + سيولة مرتفعة + RSI غير مشبع بيع
                is_trend_down = (cp < cur_ema20) and (cur_ema20 < cur_ema50)
                is_rsi_safe_short = (cur_rsi > 32) and (cur_rsi < 55)

                if is_trend_up and is_volume_high and is_rsi_safe_long:
                    # حساب الهدف ووقف الخسارة بناءً على تذبذب العملة (ATR) بنسبة مخاطر العائد 1:2
                    tp = cp + (cur_atr * 2.5)
                    sl = cp - (cur_atr * 1.25)
                    
                    msg = (f"💎 **إستراتيجية احترافية مؤكدة (LONG)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الحالة: توافق الاتجاه + سيولة قوية + RSI ({round(cur_rsi, 1)})\n\n"
                           f"📥 سعر الدخول: `{format_price(cp)}`\n"
                           f"🎯 الهدف المقترح (TP): `{format_price(tp)}`\n"
                           f"🛑 وقف الخسارة (SL): `{format_price(sl)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    
                    if send_telegram_alert(msg):
                        alerts_sent += 1

                elif is_trend_down and is_volume_high and is_rsi_safe_short:
                    tp = cp - (cur_atr * 2.5)
                    sl = cp + (cur_atr * 1.25)
                    
                    msg = (f"💎 **إستراتيجية احترافية مؤكدة (SHORT)**\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{symbol}\n"
                           f"⏱ الوقت: `{current_time}`\n"
                           f"📊 الحالة: هبوط متوافق مع السيولة + RSI ({round(cur_rsi, 1)})\n\n"
                           f"📥 سعر الدخول: `{format_price(cp)}`\n"
                           f"🎯 الهدف المقترح (TP): `{format_price(tp)}`\n"
                           f"🛑 وقف الخسارة (SL): `{format_price(sl)}`\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"📈 [رابط الشارت المباشر]({chart})")
                    
                    if send_telegram_alert(msg):
                        alerts_sent += 1

        except Exception as e:
            continue
            
    print(f"✨ اكتمل الفحص الاحترافي. الصفقات المؤكدة المكتشفة: {alerts_sent}")

if __name__ == "__main__":
    main()
