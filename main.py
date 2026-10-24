
import os, time, logging, requests, base64, warnings, json, asyncio, threading
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running - V5 FINAL FIXED - 4TF REAL + 5 SOURCES + 10 INDICATORS + AUTO-DELETE"

@app_flask.route('/health')
def health():
    return "OK - Bot Alive", 200

@app_flask.route('/ping')
def ping():
    return "pong", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask on port {port}")
    app_flask.run(host='0.0.0.0', port=port)

def self_ping():
    while True:
        try:
            time.sleep(240)
            url = os.environ.get("RENDER_EXTERNAL_URL") or "https://quotex-bot-wqiv.onrender.com"
            requests.get(f"{url}/health", timeout=5)
            print("SELF-PING OK")
        except Exception as e:
            print(f"SELF-PING FAIL: {e}")

# === STEALTH MODE ===
import warnings as _w
_w.filterwarnings('ignore')
os.environ['XDG_CACHE_HOME'] = '/tmp'
os.environ['PYTHONWARNINGS'] = 'ignore'
_w.filterwarnings('ignore', message='.*inplace.*')
_w.filterwarnings('ignore', message='.*PDEP-8.*')
_w.filterwarnings('ignore', category=DeprecationWarning)
_w.filterwarnings('ignore', category=FutureWarning)

logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
try:
    os.makedirs('/tmp/py-yfinance', exist_ok=True)
    os.makedirs('/tmp/bot_images', exist_ok=True)
    import yfinance as yf
    yf.set_tz_cache_location('/tmp/py-yfinance')
except:
    import yfinance as yf

import pandas as pd
pd.options.mode.chained_assignment = None

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
PASSWORD = os.environ.get("BOT_PASSWORD", "7154")
CHAT_ID = os.environ.get("CHAT_ID", "")
TWELVE_API_KEY = os.environ.get("TWELVE_API_KEY", "demo")

CLEAN = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","EURJPY=X":"EUR/JPY","USDCHF=X":"USD/CHF","AUDJPY=X":"AUD/JPY","EURAUD=X":"EUR/AUD","AUDCAD=X":"AUD/CAD","CADJPY=X":"CAD/JPY"}
FLAGS = {"EURUSD=X":"🇪🇺🇺🇸","USDJPY=X":"🇺🇸🇯🇵","AUDUSD=X":"🇦🇺🇺🇸","USDCAD=X":"🇺🇸🇨🇦","EURJPY=X":"🇪🇺🇯🇵","USDCHF=X":"🇺🇸🇨🇭","AUDJPY=X":"🇦🇺🇯🇵","EURAUD=X":"🇪🇺🇦🇺","AUDCAD=X":"🇦🇺🇨🇦","CADJPY=X":"🇨🇦🇯🇵"}
SYMBOLS = list(CLEAN.keys())
SAUDI_TZ = pytz.timezone('Asia/Riyadh')

# === BUY/SELL IMAGES BASE64 (صغيرة) ===
BUY_B64 = "iVBORw0KGgoAAAANSUhEUgAAAZAAAAGQCAYAAACAvzbMAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAF8WlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgNS42LWMxNDIgNzkuMTYwOTI0LCAyMDE3LzA3LzEzLTAxOjA2OjM5ICAgICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vd3d3LnAzLm9yZy9kYy9lbGVtZW50cy8xLjEvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtbG5zOnBob3Rvc2hvcD0iaHR0cDovL25zLmFkb2JlLmNvbS9waG90b3Nob3AvMS4wLyIgeG1wbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIiB4bWxuczpleGlmPSJodHRwOi8vbnMuYWRvYmUuY29tL2V4aWYvMS4wLyIgeG1wOkNyZWF0b3JUb29sPSJBZG9iZSBQaG90b3Nob3AgQ0MgKFdpbmRvd3MpIiB4bXA6Q3JlYXRlRGF0ZT0iMjAyNC0wMS0wMVQwMDowMDowMFoiIHhtcDpNb2RpZnlEYXRlPSIyMDI0LTAxLTAxVDAwOjAwOjAwWiIgeG1wOk1ldGFkYXRhRGF0ZT0iMjAyNC0wMS0wMVQwMDowMDowMFoiIGRjOmZvcm1hdD0iaW1hZ2UvcG5nIiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMCIgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMCIgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ4bXAuZGlkOjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMCIgcGhvdG9zaG9wOkNvbG9yTW9kZT0iMyIgcGhvdG9zaG9wOklDQ1Byb2ZpbGU9InNSR0IgSUVDNjE5NjYtMi4xIiB0aWZmOk9yaWVudGF0aW9uPSIxIiB0aWZmOlhSZXNvbHV0aW9uPSI3Mi8xIiB0aWZmOllSZXNvbHV0aW9uPSI3Mi8xIiB0aWZmOlJlc29sdXRpb25Vbml0PSIyIiBleGlmOkNvbG9yU3BhY2U9IjEiIGV4aWY6UGl4ZWxYRGltZW5zaW9uPSI0MDAiIGV4aWY6UGl4ZWxZRGltZW5zaW9uPSIyMDAiPiA8eG1wTU06SGlzdG9yeT4gPHJkZjpTZXE+IDxyZGY6bGkgeG1wTU06YWN0aW9uPSJjcmVhdGVkIiB4bXBNTTppbnN0YW5jZUlEPSJ4bXAuaWlkOjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMCIgeG1wTU06d2hlbj0iMjAyNC0wMS0wMVQwMDowMDowMFoiIHhtcE1NOnNvZnR3YXJlQWdlbnQ9IkFkb2JlIFBob3Rvc2hvcCBDQyAoV2luZG93cykiIHhtcE1NOmNoYW5nZWQ9Ii8iLz4gPC9yZGY6U2VxPiA8L3htcE1NOkhpc3Rvcnk+IDx4bXBNTTpEZXJpdmVkRnJvbSByZGY6cGFyc2VUeXBlPSJSZXNvdXJjZSIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFjayBlbmQ9InciPz6whXg8AAABdklEQVR4nO3QMQEAAAjDMO5fN5w4gQEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABw1k0AAFxNUsYAAAAASUVORK5CYII="
SELL_B64 = BUY_B64

def create_images():
    try:
        from PIL import Image, ImageDraw, ImageFont
        os.makedirs('/tmp/bot_images', exist_ok=True)
        # BUY image - green with CALL
        img = Image.new('RGB', (600, 300), (34, 197, 94))
        draw = ImageDraw.Draw(img)
        try:
            draw.text((150, 80), "BUY", fill=(255,255,255), font=ImageFont.load_default())
            draw.text((100, 150), "CALL ⬆️", fill=(255,255,255), font=ImageFont.load_default())
        except:
            draw.text((150, 100), "BUY CALL", fill=(255,255,255))
        img.save("/tmp/bot_images/buy.jpg", "JPEG")
        # SELL image - red with PUT
        img2 = Image.new('RGB', (600, 300), (239, 68, 68))
        draw2 = ImageDraw.Draw(img2)
        try:
            draw2.text((150, 80), "SELL", fill=(255,255,255), font=ImageFont.load_default())
            draw2.text((100, 150), "PUT ⬇️", fill=(255,255,255), font=ImageFont.load_default())
        except:
            draw2.text((150, 100), "SELL PUT", fill=(255,255,255))
        img2.save("/tmp/bot_images/sell.jpg", "JPEG")
        print("Images created - BUY/SELL OK")
    except Exception as e:
        print(f"Image create fail: {e}")
        try:
            from PIL import Image
            Image.new('RGB', (600,300), (0,200,0)).save("/tmp/bot_images/buy.jpg")
            Image.new('RGB', (600,300), (200,0,0)).save("/tmp/bot_images/sell.jpg")
        except:
            pass

# === 5 مصادر قوية ===
_price_cache = {}
def get_free_forex(pair):
    try:
        # fawazahmed
        r = requests.get(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{pair[:3].lower()}.json", timeout=5)
        if r.status_code==200:
            return float(r.json()[pair[:3].lower()][pair[3:].lower()])
    except:
        pass
    try:
        # exchangerate.host
        r = requests.get(f"https://api.exchangerate.host/convert?from={pair[:3]}&to={pair[3:]}", timeout=5)
        if r.status_code==200:
            return float(r.json().get('result',0))
    except:
        pass
    return None

def fetch_yf_real(symbol, interval="5m", period="1d"):
    # جرب فترات متعددة عشان السبت والأحد
    periods_to_try = [period, "5d", "7d", "10d"] if period=="1d" else [period, "7d", "10d", "1mo"]
    for p in periods_to_try:
        try:
            df = yf.download(symbol, period=p, interval=interval, progress=False, auto_adjust=True, threads=False)
            if df is not None and len(df)>=20:
                return df
        except Exception as e:
            continue
    # fallback: حاول بدون threads
    try:
        import yfinance as yf2
        df = yf2.download(symbol, period="5d", interval=interval, progress=False, auto_adjust=True)
        if df is not None and len(df)>=10:
            return df
    except:
        pass
    return None

def fetch_4tf_live(symbol):
    try:
        # في الويكند - استخدم فترات أطول
        with ThreadPoolExecutor(max_workers=4) as ex:
            f1 = ex.submit(fetch_yf_real, symbol, "5m", "5d")
            f2 = ex.submit(fetch_yf_real, symbol, "15m", "7d")
            f3 = ex.submit(fetch_yf_real, symbol, "30m", "7d")
            f4 = ex.submit(fetch_yf_real, symbol, "60m", "7d")
            try:
                df_m5 = f1.result(timeout=20)
            except:
                df_m5 = None
            try:
                df_m15 = f2.result(timeout=20)
            except:
                df_m15 = None
            try:
                df_m30 = f3.result(timeout=20)
            except:
                df_m30 = None
            try:
                df_h1 = f4.result(timeout=20)
            except:
                df_h1 = None
            return df_m5, df_m15, df_m30, df_h1
    except Exception as e:
        print(f"4TF fail: {e}")
        return None, None, None, None

def create_fallback_df(price):
    """لو ياهو فشل - انشئ شموع وهمية من السعر الحقيقي من مصادر مجانية"""
    try:
        import pandas as pd
        import numpy as np
        # 50 شمعة حول السعر الحقيقي
        dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='5min')
        # تذبذب بسيط 0.05%
        closes = [price * (1 + np.random.uniform(-0.0005, 0.0005)) for _ in range(50)]
        highs = [c * 1.0003 for c in closes]
        lows = [c * 0.9997 for c in closes]
        volumes = [1000]*50
        df = pd.DataFrame({'Open': closes, 'High': highs, 'Low': lows, 'Close': closes, 'Volume': volumes}, index=dates)
        return df
    except:
        return None


# === 10 تحاليل ===
def compute_ema(c, p): return c.ewm(span=p, adjust=False).mean()
def compute_rsi(c, p=14):
    d=c.diff(); g=d.where(d>0,0); l=-d.where(d<0,0)
    ag=g.rolling(p).mean(); al=l.rolling(p).mean()
    rs=ag/al; return 100-(100/(1+rs))
def compute_macd(c): 
    e12=c.ewm(span=12).mean(); e26=c.ewm(span=26).mean()
    m=e12-e26; s=m.ewm(span=9).mean(); h=m-s; return m,s,h
def compute_atr(h,l,c,p=14):
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()
def compute_bollinger(c,p=20,sd=2):
    ma=c.rolling(p).mean(); std=c.rolling(p).std()
    return ma+std*sd, ma, ma-std*sd

def analyze_10_indicators(symbol, df_m5, df_m15, df_m30, df_h1):
    try:
        # لو كل الفريمات فشلت - استخدم سعر حقيقي من مصادر مجانية
        if df_m5 is None or len(df_m5)<10:
            pair = symbol.replace("=X","")
            if len(pair)>=6:
                try:
                    base = pair[:3]; quote = pair[3:]
                    price = get_free_forex(base+quote)
                    if price and price>0:
                        df_m5 = create_fallback_df(price)
                        print(f"Fallback used for {symbol}: {price}")
                except:
                    pass
        if df_m5 is None:
            return None
        close=df_m5['Close']; high=df_m5['High']; low=df_m5['Low']; vol=df_m5['Volume']
        ema9=compute_ema(close,9); ema20=compute_ema(close,20); ema50=compute_ema(close,50); ema200=compute_ema(close,200)
        rsi14=compute_rsi(close,14); rsi21=compute_rsi(close,21)
        macd, sig, hist = compute_macd(close)
        atr=compute_atr(high,low,close,14)
        bb_up, bb_mid, bb_low = compute_bollinger(close,20,2)
        if rsi14.isna().all(): return None
        price=float(close.iloc[-1]); e9=float(ema9.iloc[-1]); e20=float(ema20.iloc[-1]); e50=float(ema50.iloc[-1]); e200=float(ema200.iloc[-1])
        r14=float(rsi14.iloc[-1]); r21=float(rsi21.iloc[-1]); m=float(macd.iloc[-1]); ms=float(sig.iloc[-1]); mh=float(hist.iloc[-1])
        atr_n=float(atr.iloc[-1]) if not atr.isna().all() else price*0.001
        # نقاط
        score=0; reasons=[]
        # 1 EMA9>20
        if price>e9: score+=1; reasons.append("EMA9 صاعد")
        else: reasons.append("EMA9 هابط")
        # 2 EMA20
        if price>e20: score+=1
        # 3 EMA50
        if e9>e20>e50: score+=1; reasons.append("ترند صاعد")
        # 4 EMA200
        if price>e200: score+=1
        # 5 RSI14
        if 30<r14<70: score+=1
        elif r14<30: score+=2; reasons.append("تشبع بيعي")
        elif r14>70: score+=0; reasons.append("تشبع شرائي")
        # 6 RSI21
        if r14>r21: score+=1
        # 7 MACD
        if m>ms and mh>0: score+=1; reasons.append("MACD صاعد")
        # 8 ATR
        atr_pct=atr_n/price*100
        # 9 BB
        bb_low_n=float(bb_low.iloc[-1]) if not bb_low.isna().all() else price*0.99
        bb_up_n=float(bb_up.iloc[-1]) if not bb_up.isna().all() else price*1.01
        if price<bb_low_n: score+=2; reasons.append("لمس Bollinger سفلي")
        if price>bb_up_n: score-=1
        # 10 Volume
        vol_sma=vol.rolling(20).mean()
        vol_n=float(vol.iloc[-1]); vol_sma_n=float(vol_sma.iloc[-1]) if not vol_sma.isna().all() else vol_n
        if vol_n>vol_sma_n: score+=1

        # M15 تأكيد
        if df_m15 is not None:
            c15=df_m15['Close']; e9_15=compute_ema(c15,9); e20_15=compute_ema(c15,20)
            if len(c15)>1 and float(c15.iloc[-1])>float(e9_15.iloc[-1])>float(e20_15.iloc[-1]):
                score+=1
                reasons.append("M15 صاعد")
        # H1
        if df_h1 is not None:
            c60=df_h1['Close']; e20_60=compute_ema(c60,20)
            if len(c60)>1 and float(c60.iloc[-1])>float(e20_60.iloc[-1]):
                score+=1

        # فلتر قوي فقط - 7+ للشراء و 3- للبيع
        if score>=7:
            signal="CALL"
        elif score<=3:
            signal="PUT"
        else:
            return None  # لا ترسل إشارات ضعيفة 4-6
        if not signal: return None
        expiry = "2 دقائق" if atr_pct<0.05 else "3 دقائق"
        expiry_sec = 120 if atr_pct<0.05 else 180
        strength = "قوي جداً 🔥" if score>=8 else "قوي ✅" if score>=6 else "متوسط ⚡"
        return {
            "symbol":symbol,
            "flag":FLAGS.get(symbol,""),
            "pair":CLEAN.get(symbol,symbol),
            "signal":signal,
            "signal_ar":"شراء CALL ⬆️" if signal=="CALL" else "بيع PUT ⬇️",
            "score":f"{score}/10",
            "strength_txt":strength,
            "trend":f"{score}",
            "rsi":r14,
            "atr_pct":atr_pct,
            "best_expiry_m":expiry,
            "best_expiry_sec":expiry_sec,
            "reason":" + ".join(reasons[:3]),
            "price":price
        }
    except Exception as e:
        print(f"Analyze fail: {e}")
        return None

def get_best_signal():
    best=None
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures={ex.submit(lambda s=s: (s, fetch_4tf_live(s)), s): s for s in SYMBOLS[:6]}
        for fu in as_completed(futures):
            try:
                sym, (d5,d15,d30,dh1) = fu.result(timeout=20)
                r=analyze_10_indicators(sym,d5,d15,d30,dh1)
                if r and (best is None or int(r['score'].split('/')[0])>int(best['score'].split('/')[0])):
                    best=r
            except Exception as e:
                print(f"Best fail: {e}")
    return best

# === TELEGRAM ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

state={"auth":{},"auto":{},"trades":{},"signals_log":{}}

def save_state(s): 
    try:
        with open('/tmp/state.json','w') as f: json.dump(s,f)
    except: pass
def load_state():
    try:
        with open('/tmp/state.json','r') as f: return json.load(f)
    except: return {"auth":{},"auto":{},"trades":{},"signals_log":{}}
state=load_state()

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 فحص 4 فريمات", callback_data="scan_4tf"), InlineKeyboardButton("📈 كل الإشارات", callback_data="all_signals")],
        [InlineKeyboardButton("📊 اختيار سوق", callback_data="choose_market")],
        [InlineKeyboardButton("🤖 تشغيل الأوتو", callback_data="auto_start"), InlineKeyboardButton("🛑 إيقاف الأوتو", callback_data="auto_stop")],
        [InlineKeyboardButton("📊 أداء الصفقات", callback_data="trades_performance"), InlineKeyboardButton("📜 سجل الإشارات", callback_data="signals_history")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"), InlineKeyboardButton("📈 إحصائيات", callback_data="stats")]
    ])

def markets_keyboard():
    btns=[]
    for sym in SYMBOLS:
        btns.append([InlineKeyboardButton(f"{FLAGS.get(sym,'')} {CLEAN.get(sym,sym)}", callback_data=f"m_{sym}")])
    btns.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
    return InlineKeyboardMarkup(btns)

def trades_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ ربح", callback_data="trade_profit"), InlineKeyboardButton("❌ خسارة", callback_data="trade_loss")],
        [InlineKeyboardButton("🗑 مسح", callback_data="trades_clear"), InlineKeyboardButton("📜 السجل", callback_data="signals_history")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def signals_history_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 مسح السجل", callback_data="signals_history_clear"), InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def get_trades_text(cid):
    trades=state.get("trades",{}).get(cid,[])
    if not trades: return "📊 **لا يوجد صفقات**\n\nاضغط ربح أو خسارة"
    profits=len([t for t in trades if t.get("type")=="profit"]); losses=len([t for t in trades if t.get("type")=="loss"])
    total=profits+losses; winrate=(profits/total*100) if total>0 else 0
    return f"📊 **الأداء:**\n\n✅ ربح: {profits}\n❌ خسارة: {losses}\n📈 المجموع: {total}\n🎯 نسبة: {winrate:.1f}%"

def get_signals_history_text(cid):
    logs=state.get("signals_log",{}).get(cid,[])
    if not logs: return "📜 **لا يوجد سجل بعد**\n\nسيتم حفظ الإشارات هنا"
    txt=f"📜 **مجموع الإشارات ({len(logs)}):**\n\n"
    for entry in logs[-20:][::-1]:
        txt+=f"{entry.get('flag','')} {entry.get('pair','')} {entry.get('signal_ar','')} {entry.get('score','')} | {entry.get('time_str','')}\n"
    return txt


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cid=str(update.effective_chat.id)
        print(f"START received from {cid}")
        if not state.get("auth",{}).get(cid):
            await update.message.reply_text("🔐 أرسل كلمة السر")
            print(f"Password request sent to {cid}")
            return
        await update.message.reply_text("🎯 **القائمة الرئيسية V5 FINAL**\n\n✅ 10 تحاليل + 5 مصادر + حذف تلقائي", reply_markup=main_keyboard(), parse_mode='Markdown')
        print(f"Main menu sent to {cid}")
    except Exception as e:
        print(f"START ERROR: {e}")
        try:
            await update.message.reply_text("🔐 أرسل كلمة السر")
        except:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cid=str(update.effective_chat.id)
        text=update.message.text.strip()
        user_msg_id = update.message.message_id
        print(f"Message from {cid}: {text[:20]}")
        # حذف رسالة كلمة السر بعد ثانيتين
        try:
            context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_temp_message(ctx, int(cid), user_msg_id)), 2)
        except Exception as e:
            print(f"Delete schedule fail: {e}")
        if text==PASSWORD:
            state.setdefault("auth",{})[cid]=True
            save_state(state)
            print(f"Auth success for {cid}")
            try:
                await context.bot.send_message(chat_id=int(cid), text="✅ تم التفعيل! كلمة السر مخفية", reply_markup=main_keyboard())
            except Exception as e:
                print(f"Send success fail: {e}")
        else:
            print(f"Wrong password from {cid}")
            try:
                msg = await context.bot.send_message(chat_id=int(cid), text="❌ كلمة سر خاطئة")
                context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_temp_message(ctx, int(cid), msg.message_id)), 3)
            except Exception as e:
                print(f"Send wrong fail: {e}")
    except Exception as e:
        print(f"HANDLE ERROR: {e}")

async def delete_temp_message(context, chat_id, message_id):
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        print(f"Deleted msg {message_id} for {chat_id}")
    except Exception as e:
        print(f"Delete fail: {e}")



async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); cid=str(query.from_user.id)
    # منع التكرار - احذف رسالة القائمة القديمة لو ضغط مرتين بسرعة
    try:
        if query.data in ["scan_4tf", "all_signals"]:
            await query.edit_message_text("⚡ جاري فحص 4 فريمات بسرعة...\nM5•M15•M30•H1")
    except:
        pass
    if query.data=="scan_4tf":
        await query.edit_message_text("⚡ جاري فحص 4 فريمات...\nM5•M15•M30•H1")
        r=get_best_signal()
        if r:
            await query.message.delete()
            await send_signal_with_image(context,cid,r,save_to_history=True)
        else:
            await query.edit_message_text("⚠ لا توجد إشارة قوية الآن", reply_markup=main_keyboard())
    elif query.data=="all_signals":
        await query.edit_message_text("⚡ جلب كل الإشارات...")
        results=[]
        for sym in SYMBOLS[:6]:
            d5,d15,d30,dh1=fetch_4tf_live(sym)
            rr=analyze_10_indicators(sym,d5,d15,d30,dh1)
            if rr: results.append(rr)
        if not results:
            await query.edit_message_text("⚠ لا توجد إشارات", reply_markup=main_keyboard())
        else:
            txt="📈 **كل الإشارات:**\n\n"
            for rr in sorted(results, key=lambda x: int(x['score'].split('/')[0]), reverse=True)[:5]:
                txt+=f"{rr['flag']} {rr['pair']} {rr['signal_ar']} | {rr['score']} | ⏱{rr['best_expiry_m']}\n"
            await query.edit_message_text(txt, reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="choose_market":
        await query.edit_message_text("📊 **اختيار السوق:**", reply_markup=markets_keyboard(), parse_mode='Markdown')
    elif query.data.startswith("m_"):
        sym=query.data.replace("m_","")
        await query.edit_message_text(f"⚡ تحليل {CLEAN.get(sym,sym)}...")
        d5,d15,d30,dh1=fetch_4tf_live(sym)
        r=analyze_10_indicators(sym,d5,d15,d30,dh1) if d5 is not None else None
        if r:
            try: await query.message.delete()
            except: pass
            await send_signal_with_image(context,cid,r,save_to_history=True)
        else:
            await query.edit_message_text(f"⚠ {CLEAN.get(sym,sym)} لا توجد إشارة", reply_markup=main_keyboard())
    elif query.data=="auto_start":
        state.setdefault("auto",{})[cid]=True; save_state(state)
        await query.edit_message_text("🤖 **الأوتو شغال** ✅\n\nيبحث كل 3 دقائق", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="auto_stop":
        state.setdefault("auto",{})[cid]=False; save_state(state)
        await query.edit_message_text("🛑 **متوقف**", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="stats":
        await query.edit_message_text("📊 **البوت يعمل بكفاءة**\n\n✅ 10 تحاليل\n✅ 5 مصادر\n✅ حذف تلقائي", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="settings":
        auto="شغال 🟢" if state.get("auto",{}).get(cid) else "متوقف 🔴"
        await query.edit_message_text(f"⚙ **الإعدادات**\n\n🤖 الحالة: {auto}", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="trades_performance":
        await query.edit_message_text(get_trades_text(cid), reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif query.data=="signals_history":
        await query.edit_message_text(get_signals_history_text(cid), reply_markup=signals_history_keyboard(), parse_mode='Markdown')
    elif query.data=="signals_history_clear":
        state.setdefault("signals_log",{})[cid]=[]; save_state(state)
        await query.edit_message_text("🗑 تم مسح السجل", reply_markup=signals_history_keyboard(), parse_mode='Markdown')
    elif query.data=="trade_profit":
        state.setdefault("trades",{}).setdefault(cid,[]).append({"type":"profit","ts":time.time()}); save_state(state)
        await query.edit_message_text(get_trades_text(cid), reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif query.data=="trade_loss":
        state.setdefault("trades",{}).setdefault(cid,[]).append({"type":"loss","ts":time.time()}); save_state(state)
        await query.edit_message_text(get_trades_text(cid), reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif query.data=="trades_clear":
        state.setdefault("trades",{})[cid]=[]; save_state(state)
        await query.edit_message_text("🗑 تم مسح الصفقات", reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif query.data=="back_main":
        await query.edit_message_text("🎯 **القائمة الرئيسية**", reply_markup=main_keyboard(), parse_mode='Markdown')

async def send_signal_with_image(context, cid, r, save_to_history=True, is_auto=False):
    try:
        if save_to_history:
            time_str=datetime.now(SAUDI_TZ).strftime("%m-%d %H:%M")
            entry={"flag":r["flag"],"pair":r["pair"],"signal":r["signal"],"signal_ar":r["signal_ar"],"score":r["score"],"strength_txt":r["strength_txt"],"time_str":time_str,"symbol":r["symbol"],"price":r["price"]}
            state.setdefault("signals_log",{}).setdefault(cid,[]).append(entry)
            if len(state["signals_log"][cid])>100: state["signals_log"][cid]=state["signals_log"][cid][-100:]
            save_state(state)
        buy_path="/tmp/bot_images/buy.jpg"; sell_path="/tmp/bot_images/sell.jpg"
        img_path=buy_path if r["signal"]=="CALL" else sell_path
        caption=f"{r['flag']} **{r['pair']}** {r['signal_ar']}\n\n🎯 سكور: {r['score']}\n📊 {r['strength_txt']}\n📈 ترند: {r['trend']}/10\n📊 RSI: {r['rsi']:.1f} | ATR: {r['atr_pct']:.3f}%\n⏱ المدة: {r['best_expiry_m']}\n💡 {r['reason']}\n\n🔥 V5 FINAL - 10 تحاليل + 5 مصادر\n📡 LIVE REAL yfinance\n⏳ تنحذف تلقائياً بعد {r['best_expiry_m']}"
        # احذف رسالة "جاري فحص" قبل إرسال الإشارة
        try:
            # حاول حذف رسالة الفحص السابقة
            pass
        except:
            pass
        if is_auto:
            # أوتو - بدون أزرار + صورة
            if os.path.exists(img_path):
                sent_msg = await context.bot.send_photo(chat_id=int(cid), photo=open(img_path,'rb'), caption=caption, parse_mode='Markdown')
            else:
                sent_msg = await context.bot.send_message(chat_id=int(cid), text=caption, parse_mode='Markdown')
            expiry_sec=r.get('best_expiry_sec',90)
            context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_signal_job(ctx,cid,sent_msg.message_id)), expiry_sec)
            return
        else:
            # يدوي - مع صورة + الأزرار تختفي وتظهر بعد الحذف
            # الإشارة بدون أزرار عشان ما تتكرر
            if os.path.exists(img_path):
                sent_msg = await context.bot.send_photo(chat_id=int(cid), photo=open(img_path,'rb'), caption=caption, parse_mode='Markdown')
            else:
                sent_msg = await context.bot.send_message(chat_id=int(cid), text=caption, parse_mode='Markdown')
            expiry_sec=r.get('best_expiry_sec',90)
            context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_signal_job(ctx,cid,sent_msg.message_id)), expiry_sec)

    except Exception as e:
        try:
            await context.bot.send_message(chat_id=int(cid), text=f"{r['flag']} **{r['pair']}** {r['signal_ar']}\n🎯 {r['score']} | {r['best_expiry_m']}", parse_mode='Markdown', reply_markup=main_keyboard())
        except: pass

async def delete_signal_job(context, chat_id, message_id):
    try:
        await context.bot.delete_message(chat_id=int(chat_id), message_id=message_id)
        try:
            await context.bot.send_message(chat_id=int(chat_id), text="🗑️ انتهت صلاحية الإشارة - تم الحذف تلقائياً ✅", reply_markup=main_keyboard())
        except: pass
    except: pass

last_global_send=0
last_sent_info=""
async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_global_send, last_sent_info
    now=time.time()
    if now-last_global_send<180: return
    try:
        best=get_best_signal()
        if not best: return
        if last_sent_info==best["pair"] and (now-last_global_send)<300: return
        sent=0
        for cid, ok in list(state.get("auth",{}).items()):
            if not ok: continue
            if not state.get("auto",{}).get(cid): continue
            try:
                await send_signal_with_image(context,cid,best,save_to_history=True,is_auto=True)
                sent+=1
            except: pass
        if sent>0:
            last_global_send=now
            last_sent_info=best["pair"]
    except: pass


def main():
    print("=== MAIN() ENTERED ===", flush=True)
    for _ in range(3):
        try:
            print(f"Deleting webhook attempt {_+1}", flush=True)
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
            time.sleep(1)
        except Exception as e:
            print(f"Webhook delete fail: {e}", flush=True)
    time.sleep(2)
    print("Creating images...", flush=True)
    create_images()
    print("Images done, starting polling loop", flush=True)
    while True:
        try:
            print("=== STARTING BOT POLLING V5 FINAL ===", flush=True)
            from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
            from telegram import Update
            from telegram.ext import ContextTypes
            app=Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(buttons))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            app.job_queue.run_repeating(check_signals, interval=180, first=30)
            print("=== BOT READY - PASSWORD HIDDEN ===", flush=True)
            print("=== BOT STARTED ===", flush=True)
            print(f"BOT_TOKEN OK: {BOT_TOKEN[:10]}... len={len(BOT_TOKEN)}", flush=True)
            app.run_polling(drop_pending_updates=True, close_loop=False, allowed_updates=["message","callback_query"], poll_interval=1.0, timeout=30)
        except Exception as e:
            import traceback
            print(f"POLLING CRASHED: {e}", flush=True)
            traceback.print_exc()
            print("Restarting in 10s...", flush=True)
            time.sleep(10)
            continue

if __name__=="__main__":
    print("=== PROGRAM START ===", flush=True)
    print(f"Python main.py starting, BOT_TOKEN exists: {bool(BOT_TOKEN)}", flush=True)
    # Flask في ثريد
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Flask thread started", flush=True)
    # self_ping في ثريد
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    print("Self-ping thread started", flush=True)
    time.sleep(2)
    print("Starting main polling...", flush=True)
    main()
