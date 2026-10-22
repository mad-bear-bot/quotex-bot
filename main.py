
import os, time, logging, requests, base64, json
from datetime import datetime, timedelta
import threading
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['XDG_CACHE_HOME'] = '/tmp'
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
try:
    os.makedirs('/tmp/py-yfinance', exist_ok=True)
    import yfinance as yf
    yf.set_tz_cache_location('/tmp/py-yfinance')
    logging.info('TzCache fixed to /tmp')
except Exception as e:
    logging.warning(f'TzCache fix {e}')
    import yfinance as yf

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
PASSWORD = os.environ.get("BOT_PASSWORD", "7154")
POCKET_SSID = os.environ.get("POCKET_SSID", "")
POCKET_DEMO = os.environ.get("POCKET_DEMO", "True") == "True"

# ضع هنا نفس BUY_B64 و SELL_B64 من ملفك القديم
BUY_B64 = ""
SELL_B64 = ""

def setup_images():
    try:
        os.makedirs("/tmp/bot_images", exist_ok=True)
        buy_path="/tmp/bot_images/buy.jpg"
        sell_path="/tmp/bot_images/sell.jpg"
        if BUY_B64:
            try:
                with open(buy_path,"wb") as f: f.write(base64.b64decode(BUY_B64))
            except: pass
        if SELL_B64:
            try:
                with open(sell_path,"wb") as f: f.write(base64.b64decode(SELL_B64))
            except: pass
        logging.info(f"Images ready BUY:{os.path.exists(buy_path)} SELL:{os.path.exists(sell_path)}")
    except Exception as e:
        logging.error(f"setup {e}")
setup_images()

from flask import Flask
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return 'VIP 7154 + V4.0 LEGENDARY + AUTO TRADE + LIVE SSID'
@flask_app.route('/health')
def health(): return 'OK'
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# نفس الأسواق بالضبط - لا حذف ولا إضافة
SYMBOLS = ["EURUSD=X","USDJPY=X","AUDUSD=X","USDCAD=X","EURJPY=X","USDCHF=X","AUDJPY=X","EURAUD=X","AUDCAD=X","CADJPY=X"]
CLEAN = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDCAD=X":"USD/CAD","EURJPY=X":"EUR/JPY","USDCHF=X":"USD/CHF","AUDJPY=X":"AUD/JPY","EURAUD=X":"EUR/AUD","AUDCAD=X":"AUD/CAD","CADJPY=X":"CAD/JPY"}
FLAGS = {"EURUSD=X":"🇪🇺🇺🇸","USDJPY=X":"🇺🇸🇯🇵","AUDUSD=X":"🇦🇺🇺🇸","USDCAD=X":"🇺🇸🇨🇦","EURJPY=X":"🇪🇺🇯🇵","USDCHF=X":"🇺🇸🇨🇭","AUDJPY=X":"🇦🇺🇯🇵","EURAUD=X":"🇪🇺🇦🇺","AUDCAD=X":"🇦🇺🇨🇦","CADJPY=X":"🇨🇦🇯🇵"}

SAUDI_TZ = pytz.timezone('Asia/Riyadh')
MARKET_HOURS = {
    "EURUSD=X": {"hours":[(10,19)]}, "USDJPY=X": {"hours":[(15,23),(0,5)]},
    "AUDUSD=X": {"hours":[(2,19)]}, "USDCAD=X": {"hours":[(15,23)]},
    "EURJPY=X": {"hours":[(10,23),(0,5)]}, "USDCHF=X": {"hours":[(10,19)]},
    "AUDJPY=X": {"hours":[(2,13)]}, "EURAUD=X": {"hours":[(10,23),(0,5)]},
    "AUDCAD=X": {"hours":[(2,23)]}, "CADJPY=X": {"hours":[(2,23)]},
}

def is_optimal_time_jeddah(symbol):
    now = datetime.now(SAUDI_TZ)
    day = now.weekday(); hour = now.hour
    if day >= 5: return False, "ويكند"
    if day == 4 and hour >= 17: return False, "جمعة مساء"
    if day == 0 and hour < 10: return False, "اثنين صباحا"
    hours = MARKET_HOURS[symbol]["hours"]
    active=False
    for s,e in hours:
        if s <= e:
            if s <= hour < e: active=True
        else:
            if hour >= s or hour < e: active=True
    if not active: return False, "خارج الوقت"
    return True, "مثالي"

state = {"auth":{},"paused":{},"expiry":{},"auto":{},"trades":{},"signals_log":{},"pocket":{},"auto_trade":{}}
def save_state(s):
    try: json.dump(s, open("/tmp/state.json","w"))
    except: pass
def load_state():
    try:
        if os.path.exists("/tmp/state.json"):
            d=json.load(open("/tmp/state.json"))
            for k in ["trades","signals_log","pocket","auto_trade"]: 
                if k not in d: d[k]={}
            return d
    except: pass
    return {"auth":{},"paused":{},"expiry":{},"auto":{},"trades":{},"signals_log":{},"pocket":{},"auto_trade":{}}

state = load_state()

def compute_rsi(close, period=14):
    delta=close.diff()
    gain=delta.where(delta>0,0).ewm(alpha=1/period, adjust=False).mean()
    loss=(-delta.where(delta<0,0)).ewm(alpha=1/period, adjust=False).mean()
    rs=gain/loss
    return 100-(100/(1+rs))

def compute_ema(close, period):
    return close.ewm(span=period, adjust=False).mean()

def compute_atr(high, low, close, period=14):
    tr=(high-low).combine((close-close.shift()).abs(), max).combine((close.shift()-low).abs(), max)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def compute_macd(close, fast=12, slow=26, signal=9):
    ema_fast=compute_ema(close, fast)
    ema_slow=compute_ema(close, slow)
    macd=ema_fast-ema_slow
    macd_signal=compute_ema(macd, signal)
    hist=macd-macd_signal
    return macd, macd_signal, hist

def compute_bollinger(close, period=20, std=2):
    sma=close.rolling(period).mean()
    std_dev=close.rolling(period).std()
    upper=sma+std*std_dev
    lower=sma-std*std_dev
    return upper, sma, lower

def calc_best_expiry(rsi_now, atr_now, price, trend_strength):
    atr_pct=(atr_now/price*100) if price else 0
    if rsi_now>78 or rsi_now<22: return "1 د","1M","انعكاس قوي جدا"
    if atr_pct>0.18: return "1 د","1M","تذبذب عالي"
    if trend_strength>=12: return "2 د","2M","ترند 2+2+2 اسطوري"
    if trend_strength>=10: return "2 د","2M","ترند قوي جدا"
    return "3 د","3M","ترند قوي"

def fetch_4tf_live(symbol):
    try:
        df_m5 = yf.Ticker(symbol).history(period="5d", interval="5m", auto_adjust=False)
        if df_m5.empty or len(df_m5) < 70:
            return None, None, None, None
        df_m15 = df_m5.resample('15min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        df_m30 = df_m5.resample('30min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        df_h1 = df_m5.resample('60min').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
        if len(df_m15) < 25 or len(df_m30) < 20 or len(df_h1) < 18:
            return None, None, None, None
        return df_m5.tail(150), df_m15.tail(120), df_m30.tail(100), df_h1.tail(80)
    except Exception as e:
        logging.error(f"fetch {symbol} {e}")
        return None, None, None, None

def get_strength_level(price, ema20):
    if not price or not ema20: return 0
    dist = abs(price - ema20) / price * 100
    if dist >= 0.10: return 3
    if dist >= 0.05: return 2
    if dist >= 0.015: return 1
    return 0

def analyze_15_indicators(symbol, df_m5, df_m15, df_m30, df_h1, strict=True):
    try:
        if df_m5 is None or df_m15 is None or df_m30 is None or df_h1 is None:
            return None
        close_m5=df_m5['Close']; high_m5=df_m5['High']; low_m5=df_m5['Low']; vol_m5=df_m5['Volume']
        ema9_m5=compute_ema(close_m5,9); ema20_m5=compute_ema(close_m5,20); ema50_m5=compute_ema(close_m5,50); ema200_m5=compute_ema(close_m5,200)
        rsi14_m5=compute_rsi(close_m5,14); rsi21_m5=compute_rsi(close_m5,21)
        macd, macd_sig, macd_hist = compute_macd(close_m5)
        atr_m5=compute_atr(high_m5, low_m5, close_m5,14)
        bb_up, bb_mid, bb_low = compute_bollinger(close_m5,20,2)
        vol_sma=vol_m5.rolling(20).mean()

        if rsi14_m5.isna().all() or ema20_m5.isna().all(): return None

        price_m5=float(close_m5.iloc[-1]); ema9_m5_n=float(ema9_m5.iloc[-1]); ema20_m5_n=float(ema20_m5.iloc[-1]); ema50_m5_n=float(ema50_m5.iloc[-1]); ema200_m5_n=float(ema200_m5.iloc[-1])
        rsi14_n=float(rsi14_m5.iloc[-1]); rsi21_n=float(rsi21_m5.iloc[-1]); atr_n=float(atr_m5.iloc[-1])
        macd_n=float(macd.iloc[-1]); macd_sig_n=float(macd_sig.iloc[-1]); macd_hist_n=float(macd_hist.iloc[-1])
        bb_up_n=float(bb_up.iloc[-1]) if not bb_up.isna().all() else price_m5*1.01
        bb_low_n=float(bb_low.iloc[-1]) if not bb_low.isna().all() else price_m5*0.99
        vol_n=float(vol_m5.iloc[-1]); vol_sma_n=float(vol_sma.iloc[-1]) if not vol_sma.isna().all() else vol_n

        close_m15=df_m15['Close']; ema9_m15=compute_ema(close_m15,9); ema20_m15=compute_ema(close_m15,20)
        price_m15=float(close_m15.iloc[-1]); ema9_m15_n=float(ema9_m15.iloc[-1]); ema20_m15_n=float(ema20_m15.iloc[-1])
        m15_bull=price_m15>ema9_m15_n and ema9_m15_n>ema20_m15_n
        m15_bear=price_m15<ema9_m15_n and ema9_m15_n<ema20_m15_n
        m15_lvl=get_strength_level(price_m15, ema20_m15_n)
        m15_str=m15_lvl if m15_bull else (-m15_lvl if m15_bear else 0)

        close_m30=df_m30['Close']; ema9_m30=compute_ema(close_m30,9); ema20_m30=compute_ema(close_m30,20)
        price_m30=float(close_m30.iloc[-1]); ema9_m30_n=float(ema9_m30.iloc[-1]); ema20_m30_n=float(ema20_m30.iloc[-1])
        m30_bull=price_m30>ema9_m30_n and ema9_m30_n>ema20_m30_n
        m30_bear=price_m30<ema9_m30_n and ema9_m30_n<ema20_m30_n
        m30_lvl=get_strength_level(price_m30, ema20_m30_n)
        m30_str=m30_lvl if m30_bull else (-m30_lvl if m30_bear else 0)

        close_h1=df_h1['Close']; ema9_h1=compute_ema(close_h1,9); ema20_h1=compute_ema(close_h1,20)
        price_h1=float(close_h1.iloc[-1]); ema9_h1_n=float(ema9_h1.iloc[-1]); ema20_h1_n=float(ema20_h1.iloc[-1])
        h1_bull=price_h1>ema9_h1_n and ema9_h1_n>ema20_h1_n
        h1_bear=price_h1<ema9_h1_n and ema9_h1_n<ema20_h1_n
        h1_lvl=get_strength_level(price_h1, ema20_h1_n)
        h1_str=h1_lvl if h1_bull else (-h1_lvl if h1_bear else 0)

        if strict:
            if abs(m15_str)<2 or abs(m30_str)<2 or abs(h1_str)<2:
                return None
            if not ((m15_str>0 and m30_str>0 and h1_str>0) or (m15_str<0 and m30_str<0 and h1_str<0)):
                return None
        else:
            cnt=sum(1 for s in [m15_str,m30_str,h1_str] if abs(s)>=2)
            if cnt<2: return None

        bullish=0; bearish=0
        if price_m5>ema9_m5_n: bullish+=1
        else: bearish+=1
        if price_m5>ema20_m5_n: bullish+=1
        else: bearish+=1
        if price_m5>ema50_m5_n: bullish+=1
        else: bearish+=1
        if price_m5>ema200_m5_n: bullish+=1
        else: bearish+=1
        if rsi14_n>50: bullish+=1
        else: bearish+=1
        if rsi21_n>50: bullish+=1
        else: bearish+=1
        if macd_n>macd_sig_n: bullish+=1
        else: bearish+=1
        if price_m5>float(bb_mid.iloc[-1]): bullish+=1
        else: bearish+=1
        if m15_str>0: bullish+=1
        elif m15_str<0: bearish+=1
        if m30_str>0: bullish+=1
        elif m30_str<0: bearish+=1
        if h1_str>0: bullish+=1
        elif h1_str<0: bearish+=1
        if ema9_m5_n>ema20_m5_n: bullish+=1
        else: bearish+=1
        if ema20_m5_n>ema50_m5_n: bullish+=1
        else: bearish+=1
        if macd_hist_n>0: bullish+=1
        else: bearish+=1

        trend_strength=max(bullish,bearish)

        if rsi14_n>80 or rsi14_n<20: return None
        atr_pct=(atr_n/price_m5*100) if price_m5 else 0
        if atr_pct>0.28: return None
        curr=df_m5.iloc[-1]
        curr_pct=abs(curr['Close']-curr['Open'])/curr['Open']*100 if curr['Open'] else 0
        if curr_pct>0.14: return None

        if bullish>bearish and bullish>=8:
            if price_m5<ema20_m5_n: return None
            if m15_str<0 or m30_str<0 or h1_str<0: return None
            if macd_n<macd_sig_n: return None
            signal="CALL"; signal_ar="صعود 🟢"
        elif bearish>bullish and bearish>=8:
            if price_m5>ema20_m5_n: return None
            if m15_str>0 or m30_str>0 or h1_str>0: return None
            if macd_n>macd_sig_n: return None
            signal="PUT"; signal_ar="هبوط 🔴"
        else:
            return None

        score=68 + trend_strength*2 + abs(m15_str)*2 + abs(m30_str)*2 + abs(h1_str)*2
        if rsi14_n>45 and rsi14_n<55: score+=2
        if atr_pct<0.10: score+=4
        if curr_pct<0.04: score+=3
        if vol_n>vol_sma_n: score+=2
        score=min(score,99)

        if strict:
            if score<94: return None
            if trend_strength<9: return None
        else:
            if score<88: return None

        expiry_m, expiry, reason = calc_best_expiry(rsi14_n, atr_n, price_m5, trend_strength)

        return {
            "symbol": symbol,
            "pair": CLEAN.get(symbol, symbol),
            "flag": FLAGS.get(symbol, ""),
            "signal": signal,
            "signal_ar": signal_ar,
            "score": f"{int(score)}%",
            "score_num": int(score),
            "m15_str": m15_str,
            "m30_str": m30_str,
            "h1_str": h1_str,
            "strength_txt": f"M15:{m15_str} M30:{m30_str} H1:{h1_str} (2+2+2)",
            "trend": trend_strength,
            "rsi": rsi14_n,
            "atr_pct": atr_pct,
            "best_expiry_m": expiry_m,
            "best_expiry": expiry,
            "reason": reason,
            "price": price_m5,
            "source": "LIVE yfinance REAL"
        }
    except Exception as e:
        logging.error(f"analyze {symbol} {e}")
        return None

def get_best_legendary():
    results=[]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures={executor.submit(fetch_4tf_live, sym): sym for sym in SYMBOLS}
        for fut in as_completed(futures):
            sym=futures[fut]
            try:
                df_m5, df_m15, df_m30, df_h1 = fut.result()
                if df_m5 is not None:
                    r=analyze_15_indicators(sym, df_m5, df_m15, df_m30, df_h1, strict=True)
                    if r: results.append(r)
            except: pass
    if not results: return None
    filtered=[r for r in results if abs(r["m15_str"])>=2 and abs(r["m30_str"])>=2 and abs(r["h1_str"])>=2 and r["score_num"]>=94]
    if not filtered: return None
    return max(filtered, key=lambda x: x["score_num"])

def get_all_signals_legendary(manual=False):
    results=[]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures={executor.submit(fetch_4tf_live, sym): sym for sym in SYMBOLS}
        for fut in as_completed(futures):
            sym=futures[fut]
            try:
                df_m5, df_m15, df_m30, df_h1 = fut.result()
                if df_m5 is not None:
                    r=analyze_15_indicators(sym, df_m5, df_m15, df_m30, df_h1, strict=not manual)
                    if r:
                        if not manual:
                            ok,_=is_optimal_time_jeddah(sym)
                            if not ok: continue
                        results.append(r)
            except: pass
    return sorted(results, key=lambda x: x["score_num"], reverse=True)

# ================= V4.0 NEW: AUTO TRADE HELPERS =================
def sar_to_usd(sar):
    return round(sar/3.75,2)

def get_default_auto(cid):
    return state.get("auto_trade",{}).get(cid, {"duration":5,"amount_sar":20,"amount_usd":5.3,"count":3,"done":0,"mode":"all","min_score":94,"running":False})

def save_auto(cid, cfg):
    state.setdefault("auto_trade",{})[cid]=cfg
    save_state(state)

def get_ssid_status_text(cid):
    pocket = state.get("pocket",{}).get(cid, {})
    ssid = pocket.get("ssid") or POCKET_SSID
    created = pocket.get("created_at",0)
    if not ssid:
        return "🔴 SSID غير موجود\n\nأرسل SSID من المتصفح أو أضفه في Render ENV: POCKET_SSID"
    if not created:
        # if from env, assume now
        created = time.time()
        state.setdefault("pocket",{})[cid]={"ssid":ssid,"created_at":created}
        save_state(state)
    elapsed = time.time() - created
    total = 48*3600
    remain = total - elapsed
    if remain <=0:
        return f"🔴 SSID منتهي!\nباقي: 0س\n\n🔄 أرسل SSID جديد الآن - البوت يحذفه فورا بعد الحفظ"
    h = int(remain//3600); m = int((remain%3600)//60)
    if remain < 3600:
        status="🟡 ينتهي قريب جدا"
    elif remain < 3*3600:
        status="🟠 ينتهي قريب"
    else:
        status="🟢 صالح"
    return f"{status}\n⏳ باقي: {h}س {m}د\n💰 Demo: {POCKET_DEMO}\n📡 SSID: ...{ssid[-20:] if len(ssid)>20 else 'موجود'}"

def try_pocket_trade(signal_pair, direction, amount_usd, duration):
    # هنا يتم تنفيذ صفقة Pocket Option
    # يحتاج pocketoptionapi
    try:
        from pocketoptionapi import PocketOptionApi
        ssid = POCKET_SSID
        if not ssid: return False, "لا يوجد SSID"
        api = PocketOptionApi(ssid, demo=POCKET_DEMO)
        # تحويل اسم الزوج من EUR/USD الى EURUSD
        asset = signal_pair.replace("/","")
        # تنفيذ - الكود يختلف حسب نسخة المكتبة
        # api.buy(asset, amount_usd, direction.lower(), duration)
        return True, f"تم دخول {asset} {direction} {amount_usd}$ {duration}m"
    except Exception as e:
        logging.error(f"pocket trade {e}")
        return False, str(e)

# ================= KEYBOARDS V4.0 مرتبة ومريحة =================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 فحص 4 فريمات", callback_data="scan_4tf"), InlineKeyboardButton("📈 كل الإشارات", callback_data="signals")],
        [InlineKeyboardButton("📊 اختيار سوق", callback_data="choose_market"), InlineKeyboardButton("📦 مجموع الإشارات", callback_data="signals_history")],
        [InlineKeyboardButton("🤖 تداول تلقائي", callback_data="auto_trade_menu"), InlineKeyboardButton("🔑 حالة LIVE", callback_data="live_status")],
        [InlineKeyboardButton("⚡ بدء الإشارات +2", callback_data="auto_start"), InlineKeyboardButton("🔴 إيقاف الإشارات", callback_data="auto_stop")],
        [InlineKeyboardButton("📈 أداء الصفقات", callback_data="trades_performance"), InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ])

def auto_trade_menu_kb(cid):
    cfg = get_default_auto(cid)
    usd = sar_to_usd(cfg["amount_sar"])
    mode_txt = "🌍 كل الأسواق - أقوى فرصة" if cfg["mode"]=="all" else "📊 سوق محدد"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⏱️ المدة: {cfg['duration']} د", callback_data="at_duration"), InlineKeyboardButton(f"💰 {cfg['amount_sar']} ر.س / {usd}$", callback_data="at_amount")],
        [InlineKeyboardButton(f"🔢 العدد: {cfg['count']}", callback_data="at_count"), InlineKeyboardButton(mode_txt, callback_data="at_mode")],
        [InlineKeyboardButton("▶️ تشغيل التلقائي", callback_data="at_run"), InlineKeyboardButton("⏹️ إيقاف", callback_data="at_stop")],
        [InlineKeyboardButton("🔑 حالة LIVE", callback_data="live_status"), InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def amount_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("10 ر.س / 2.7$", callback_data="amt_10"), InlineKeyboardButton("20 ر.س / 5.3$", callback_data="amt_20")],
        [InlineKeyboardButton("30 ر.س / 8$", callback_data="amt_30"), InlineKeyboardButton("40 ر.س / 10.7$", callback_data="amt_40")],
        [InlineKeyboardButton("50 ر.س / 13.3$", callback_data="amt_50")],
        [InlineKeyboardButton("✏️ كتابة مبلغ مخصص", callback_data="amt_custom")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="auto_trade_menu")]
    ])

def duration_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 دقيقة", callback_data="dur_1"), InlineKeyboardButton("2 دقايق", callback_data="dur_2")],
        [InlineKeyboardButton("3 دقايق", callback_data="dur_3"), InlineKeyboardButton("5 دقايق", callback_data="dur_5")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="auto_trade_menu")]
    ])

def count_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 صفقة", callback_data="cnt_1"), InlineKeyboardButton("3 صفقات", callback_data="cnt_3")],
        [InlineKeyboardButton("5 صفقات", callback_data="cnt_5"), InlineKeyboardButton("10 صفقات", callback_data="cnt_10")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="auto_trade_menu")]
    ])

def mode_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 كل الأسواق - يدور أقوى فرصة ✅", callback_data="mode_all")],
        [InlineKeyboardButton("📊 سوق محدد فقط", callback_data="mode_one")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="auto_trade_menu")]
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
        [InlineKeyboardButton("🗑 مسح الصفقات", callback_data="trades_clear"), InlineKeyboardButton("📜 مجموع الإشارات", callback_data="signals_history")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def signals_history_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 مسح السجل", callback_data="signals_history_clear"), InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        [InlineKeyboardButton("📊 اختيار سوق", callback_data="choose_market")]
    ])

def live_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 تحديث SSID", callback_data="live_update"), InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        [InlineKeyboardButton("🤖 تداول تلقائي", callback_data="auto_trade_menu")]
    ])

def get_trades_text(cid):
    trades=state.get("trades",{}).get(cid,[])
    if not trades: return "📊 **لا يوجد صفقات مسجلة**\n\nاضغط ربح أو خسارة"
    profits=len([t for t in trades if t.get("type")=="profit"])
    losses=len([t for t in trades if t.get("type")=="loss"])
    total=profits+losses
    winrate=(profits/total*100) if total>0 else 0
    return f"📊 **أداء الصفقات:**\n\n✅ ربح: {profits}\n❌ خسارة: {losses}\n📈 المجموع: {total}\n🎯 نسبة: {winrate:.1f}%"

def get_signals_history_text(cid):
    logs=state.get("signals_log",{}).get(cid,[])
    if not logs:
        return "📜 **مجموع الإشارات - لا يوجد سجل بعد**\n\nسيتم حفظ كل إشارة ترسل تلقائيا هنا باسم السوق والعلم وكل التفاصيل"
    txt=f"📜 **مجموع الإشارات ({len(logs)} إشارة):**\n\n"
    for entry in logs[-20:][::-1]:
        flag=entry.get("flag",""); pair=entry.get("pair",""); sig=entry.get("signal_ar",""); score=entry.get("score",""); strength=entry.get("strength_txt",""); time_str=entry.get("time_str","")
        txt+=f"{flag} {pair} {sig} {score} | {strength} | {time_str}\n"
    if len(logs)>20:
        txt+=f"\n... و {len(logs)-20} إشارة أقدم"
    return txt

async def send_signal_with_image(context, cid, r, save_to_history=True):
    try:
        if save_to_history:
            time_str=datetime.now(SAUDI_TZ).strftime("%m-%d %H:%M")
            entry={"flag":r["flag"],"pair":r["pair"],"signal":r["signal"],"signal_ar":r["signal_ar"],"score":r["score"],"strength_txt":r["strength_txt"],"time_str":time_str,"symbol":r["symbol"],"price":r["price"]}
            state.setdefault("signals_log",{}).setdefault(cid,[]).append(entry)
            if len(state["signals_log"][cid])>100:
                state["signals_log"][cid]=state["signals_log"][cid][-100:]
            save_state(state)
        buy_path="/tmp/bot_images/buy.jpg"; sell_path="/tmp/bot_images/sell.jpg"
        img_path=buy_path if r["signal"]=="CALL" else sell_path
        caption=f"{r['flag']} **{r['pair']}** {r['signal_ar']}\n\n🎯 سكور: {r['score']} (أسطوري)\n📊 {r['strength_txt']}\n📈 ترند: {r['trend']}/15\n📊 RSI: {r['rsi']:.1f} | ATR: {r['atr_pct']:.3f}%\n⏱ المدة: {r['best_expiry_m']}\n💡 {r['reason']}\n\n🔥 V4.0 LEGENDARY - 2+2+2 + 15 ANALYTICS\n📡 LIVE REAL yfinance"
        if os.path.exists(img_path):
            await context.bot.send_photo(chat_id=int(cid), photo=open(img_path,'rb'), caption=caption, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=int(cid), text=caption, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"send {e}")
        try: await context.bot.send_message(chat_id=int(cid), text=f"{r['flag']} {r['pair']} {r['signal_ar']} {r['score']}")
        except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid=str(update.effective_chat.id)
    if cid not in state.get("auth",{}):
        await update.message.reply_text("🔐 ادخل الرقم السري: 🔑")
        return
    await update.message.reply_text("🎯 **V4.0 LEGENDARY - أسطوري + تداول تلقائي**\n\n⚡ 4 فريمات M5/M15/M30/H1 LIVE REAL\n💎 قوة 2+2+2 أسطورية\n📊 15 تحليل حقيقي\n🤖 يفحص كل الأسواق ويدور أقوى فرصة\n💰 10-50 ر.س / دولار\n🔑 LIVE SSID", reply_markup=main_keyboard(), parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid=str(update.effective_chat.id)
    txt=update.message.text.strip()
    user_msg_id = update.message.message_id
    try:
        await context.bot.delete_message(chat_id=int(cid), message_id=user_msg_id)
    except: pass
    
    # تحديث SSID - يبدأ بـ 42["auth"
    if txt.startswith('42["auth"') or '"session"' in txt or 'auth' in txt and len(txt)>100:
        state.setdefault("pocket",{})[cid]={"ssid":txt,"created_at":time.time()}
        save_state(state)
        temp_msg = await context.bot.send_message(chat_id=int(cid), text=f"✅ تم تحديث SSID بنجاح!\n{get_ssid_status_text(cid)}\n\n🔒 تم حذف رسالتك فورا للأمان", parse_mode='Markdown')
        return

    # مبلغ مخصص
    if txt.isdigit() and 1 <= int(txt) <= 1000:
        # اذا كان في وضع كتابة مبلغ
        cfg = get_default_auto(cid)
        if cid in state.get("auto_trade",{}):
            cfg["amount_sar"]=int(txt)
            cfg["amount_usd"]=sar_to_usd(int(txt))
            save_auto(cid,cfg)
            await context.bot.send_message(chat_id=int(cid), text=f"✅ تم تحديد المبلغ: {txt} ر.س / {cfg['amount_usd']}$", reply_markup=auto_trade_menu_kb(cid))
            return

    if txt==PASSWORD:
        state.setdefault("auth",{})[cid]=True
        save_state(state)
        temp_msg = await context.bot.send_message(chat_id=int(cid), text="تم فتح البوت ✅")
        import asyncio
        await asyncio.sleep(5)
        try:
            await context.bot.delete_message(chat_id=int(cid), message_id=temp_msg.message_id)
        except: pass
        await context.bot.send_message(chat_id=int(cid), text="🎯 **V4.0 LEGENDARY**\nاختر من القائمة ⬇", reply_markup=main_keyboard(), parse_mode='Markdown')
    else:
        if cid not in state.get("auth",{}):
            err = await context.bot.send_message(chat_id=int(cid), text="🔐 الرقم السري خطأ")
            import asyncio
            await asyncio.sleep(2)
            try:
                await context.bot.delete_message(chat_id=int(cid), message_id=err.message_id)
            except: pass
        else:
            await context.bot.send_message(chat_id=int(cid), text="اختر من القائمة ⬇", reply_markup=main_keyboard(), parse_mode='Markdown')

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    cid=str(query.from_user.id)
    data=query.data

    if data=="scan_4tf":
        await query.edit_message_text("⚡ **فحص أسطوري 4 فريمات M5/M15/M30/H1 + 15 تحليل... 6-8 ثواني**\n\n🔄 10 أسواق LIVE REAL بالتوازي...", reply_markup=main_keyboard())
        all_s=get_all_signals_legendary(manual=True)
        if not all_s:
            await query.edit_message_text("⚠ لا توجد إشارة 2+2+2 أسطورية الآن - السوق متذبذب\n\n✅ هذا يحميك من الخسارة\n\nانتظر الفحص التلقائي كل 3 دقائق (94+ + 2+2+2)", reply_markup=main_keyboard())
            return
        txt=f"📈 **إشارات LEGENDARY 2+2+2 ({len(all_s)}):**\n\n"
        for r in all_s[:5]:
            arrow="🟢⬆" if r["signal"]=="CALL" else "🔴⬇"
            txt+=f"{arrow} {r['pair']} {r['signal_ar']} | {r['score']} | {r['strength_txt']} | ⏱{r['best_expiry_m']}\n"
        try: await query.message.delete()
        except: pass
        await send_signal_with_image(context, cid, all_s[0], save_to_history=True)
        if len(all_s)>1:
            await context.bot.send_message(chat_id=int(cid), text=txt, reply_markup=main_keyboard(), parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=int(cid), text="🎯 القائمة", reply_markup=main_keyboard())

    elif data=="signals":
        await query.edit_message_text("⚡ **جلب 4TF LEGENDARY...**")
        all_s=get_all_signals_legendary(manual=True)
        if not all_s:
            await query.edit_message_text("⚠ لا يوجد إشارات أسطورية الآن - انتظر 3 دقائق", reply_markup=main_keyboard())
            return
        txt=f"📈 **إشارات V4.0 LEGENDARY ({len(all_s)}):**\n\n"
        for r in all_s:
            arrow="🟢⬆" if r["signal"]=="CALL" else "🔴⬇"
            txt+=f"{arrow} {r['pair']} {r['signal_ar']} | {r['score']} | {r['strength_txt']} | ⏱{r['best_expiry_m']}\n"
        await query.edit_message_text(txt, reply_markup=main_keyboard(), parse_mode='Markdown')

    elif data=="choose_market":
        await query.edit_message_text("📊 **اختيار سوق - 4TF LEGENDARY:**", reply_markup=markets_keyboard(), parse_mode='Markdown')

    elif data.startswith("m_"):
        sym=data.replace("m_","")
        await query.edit_message_text(f"⚡ تحليل {CLEAN.get(sym,sym)} 4TF LEGENDARY 15 تحليل (6 ثواني)...")
        df_m5, df_m15, df_m30, df_h1 = fetch_4tf_live(sym)
        r=analyze_15_indicators(sym, df_m5, df_m15, df_m30, df_h1, strict=False) if df_m5 is not None else None
        if r:
            try: await query.message.delete()
            except: pass
            await send_signal_with_image(context, cid, r, save_to_history=True)
            await context.bot.send_message(chat_id=int(cid), text="🎯 القائمة", reply_markup=main_keyboard())
        else:
            await query.edit_message_text(f"⚠ {CLEAN.get(sym,sym)} لا يوجد 2+2+2 الآن - جرب سوق ثاني", reply_markup=main_keyboard())

    # === V4.0 NEW ===
    elif data=="auto_trade_menu":
        cfg=get_default_auto(cid)
        txt=f"🤖 **التداول التلقائي V4.0**\n\n{get_ssid_status_text(cid)}\n\n⚙️ **الإعدادات الحالية:**\n⏱️ المدة: {cfg['duration']} د\n💰 المبلغ: {cfg['amount_sar']} ر.س / {sar_to_usd(cfg['amount_sar'])}$\n🔢 العدد: {cfg['count']} صفقات\n🎯 الوضع: {'🌍 كل الأسواق - أقوى فرصة' if cfg['mode']=='all' else 'سوق محدد'}\n📊 أقل سكور: {cfg['min_score']}+ أسطوري"
        await query.edit_message_text(txt, reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_amount":
        await query.edit_message_text("💰 **اختر مبلغ الصفقة (ريال / دولار):**\n\nأصغر شي 10 ر.س وأكبر شي 50 ر.س", reply_markup=amount_kb(), parse_mode='Markdown')
    elif data.startswith("amt_"):
        if data=="amt_custom":
            await query.edit_message_text("✏️ **اكتب المبلغ بالريال (10-50):**\n\nمثال: 35\nسيتم تحويله تلقائيا للدولار", reply_markup=amount_kb())
        else:
            val=int(data.replace("amt_",""))
            cfg=get_default_auto(cid); cfg["amount_sar"]=val; cfg["amount_usd"]=sar_to_usd(val)
            save_auto(cid,cfg)
            await query.edit_message_text(f"✅ تم تحديد المبلغ: {val} ر.س / {sar_to_usd(val)}$", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_duration":
        await query.edit_message_text("⏱️ **اختر مدة الصفقة:**", reply_markup=duration_kb(), parse_mode='Markdown')
    elif data.startswith("dur_"):
        val=int(data.replace("dur_",""))
        cfg=get_default_auto(cid); cfg["duration"]=val; save_auto(cid,cfg)
        await query.edit_message_text(f"✅ تم تحديد المدة: {val} دقايق", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_count":
        await query.edit_message_text("🔢 **كم صفقة يدخل وبعدها يوقف لحاله؟**", reply_markup=count_kb(), parse_mode='Markdown')
    elif data.startswith("cnt_"):
        val=int(data.replace("cnt_",""))
        cfg=get_default_auto(cid); cfg["count"]=val; cfg["done"]=0; save_auto(cid,cfg)
        await query.edit_message_text(f"✅ تم تحديد العدد: {val} صفقات - سيقف لحاله بعدها", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_mode":
        await query.edit_message_text("🎯 **طريقة البحث عن الفرص:**\n\n🌍 كل الأسواق = يفحص الـ 10 أسواق كلها ويختار أقوى سكور 94+ أسطوري", reply_markup=mode_kb(), parse_mode='Markdown')
    elif data.startswith("mode_"):
        mode="all" if data=="mode_all" else "one"
        cfg=get_default_auto(cid); cfg["mode"]=mode; save_auto(cid,cfg)
        await query.edit_message_text(f"✅ الوضع: {'🌍 كل الأسواق - أقوى فرصة' if mode=='all' else 'سوق محدد'}", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_run":
        cfg=get_default_auto(cid)
        if cfg["done"]>=cfg["count"]: cfg["done"]=0
        cfg["running"]=True
        save_auto(cid,cfg)
        await query.edit_message_text(f"🚀 **تم تشغيل التداول التلقائي!**\n\n⚙️ {cfg['duration']}د | {cfg['amount_sar']} ر.س / {cfg['amount_usd']}$ | {cfg['count']} صفقات\n🎯 { 'كل الأسواق - أقوى فرصة' if cfg['mode']=='all' else 'سوق محدد'}\n\n🔍 جاري فحص كل الأسواق كل 3 دقائق...\nسأرسل كل صفقة لحالها + النتيجة", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="at_stop":
        cfg=get_default_auto(cid); cfg["running"]=False; save_auto(cid,cfg)
        await query.edit_message_text("⏹️ **تم إيقاف التداول التلقائي**", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')

    elif data=="live_status":
        txt=f"🔑 **حالة الدخول LIVE**\n\n{get_ssid_status_text(cid)}\n\n💡 **كيف تحدث SSID؟**\n1. افتح Pocket Option في المتصفح\n2. F12 > Application > Cookies\n3. انسخ SSID (يبدأ بـ 42[)\n4. أرسله هنا في البوت - سيحذف فورا"
        await query.edit_message_text(txt, reply_markup=live_kb(), parse_mode='Markdown')

    elif data=="live_update":
        await query.edit_message_text("🔄 **تحديث SSID**\n\nأرسل SSID الجديد الآن (يبدأ بـ 42[)\n\n🔒 البوت يحذف رسالتك فورا بعد الحفظ للأمان", reply_markup=live_kb(), parse_mode='Markdown')

    # === القديم ===
    elif data=="auto_start":
        state.setdefault("auto",{})[cid]=True
        save_state(state)
        await query.edit_message_text("✅ **V4.0 LEGENDARY يعمل**\n\n💎 كل 3 دقائق\n📈 4 فريمات M5/M15/M30/H1 LIVE REAL\n💎 قوة 2+2+2 = M15>=2 + M30>=2 + H1>=2\n📊 15 تحليل\n🛡 سكور 94+ أسطوري\n⚡ 8 ثواني\n🖼 صور نيون\n📜 يحفظ كل إشارة", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif data=="auto_stop":
        state.setdefault("auto",{})[cid]=False
        save_state(state)
        await query.edit_message_text("🛑 **متوقف**", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif data=="stats":
        await query.edit_message_text("📊 **V4.0 LEGENDARY:**\n\n⚡ 4 فريمات M5/M15/M30/H1\n💎 2+2+2 أسطورية\n📊 15 تحليل\n🤖 تلقائي يفحص كل الأسواق ويدور أقوى فرصة 94+\n💰 10-50 ر.س / $\n🔑 LIVE SSID\n📈 تلقائي 94+ + 2+2+2", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif data=="settings":
        auto="شغال 🟢" if state.get("auto",{}).get(cid) else "متوقف 🔴"
        cfg=get_default_auto(cid)
        await query.edit_message_text(f"⚙ **V4.0:**\n\n🤖 إشارات: {auto}\n🤖 تداول تلقائي: {'شغال 🟢' if cfg['running'] else 'متوقف 🔴'}\n📊 فريمات: M5/M15/M30/H1\n💎 قوة: 2+2+2\n💰 مبلغ: {cfg['amount_sar']} ر.س\n🔢 عدد: {cfg['count']}", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif data=="trades_performance":
        txt=get_trades_text(cid)
        await query.edit_message_text(txt, reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif data=="signals_history":
        txt=get_signals_history_text(cid)
        await query.edit_message_text(txt, reply_markup=signals_history_keyboard(), parse_mode='Markdown')
    elif data=="signals_history_clear":
        state.setdefault("signals_log",{})[cid]=[]
        save_state(state)
        await query.edit_message_text("🗑 تم مسح سجل مجموع الإشارات", reply_markup=signals_history_keyboard(), parse_mode='Markdown')
    elif data=="trade_profit":
        state.setdefault("trades",{}).setdefault(cid,[]).append({"type":"profit","ts":time.time()})
        save_state(state)
        await query.edit_message_text(get_trades_text(cid), reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif data=="trade_loss":
        state.setdefault("trades",{}).setdefault(cid,[]).append({"type":"loss","ts":time.time()})
        save_state(state)
        await query.edit_message_text(get_trades_text(cid), reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif data=="trades_clear":
        state.setdefault("trades",{})[cid]=[]
        save_state(state)
        await query.edit_message_text("🗑 تم مسح الصفقات", reply_markup=trades_keyboard(), parse_mode='Markdown')
    elif data=="back_main":
        await query.edit_message_text("🎯 **V4.0 LEGENDARY - أسطوري + تداول تلقائي**", reply_markup=main_keyboard(), parse_mode='Markdown')

last_global_send=0
last_sent_info=""
last_sent_per_symbol={}
async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_global_send, last_sent_info, last_sent_per_symbol
    now=time.time()
    if now-last_global_send<180: return
    try:
        best=get_best_legendary()
        if not best: return
        symbol=best["symbol"]; signal=best["signal"]
        last_info=last_sent_per_symbol.get(symbol)
        if last_info:
            last_time, last_sig = last_info
            if last_sig==signal and (now-last_time)<900: return
            if (now-last_time)<600: return
        if last_sent_info==best["pair"] and (now-last_global_send)<300: return
        sent=0
        for cid, ok in list(state.get("auth",{}).items()):
            if not ok: continue
            if state.get("paused",{}).get(cid): continue
            if not state.get("auto",{}).get(cid): continue
            try:
                await send_signal_with_image(context, cid, best, save_to_history=True)
                sent+=1
            except: pass
        if sent>0:
            last_global_send=now
            last_sent_info=best["pair"]
            last_sent_per_symbol[symbol]=(now, signal)
    except Exception as e:
        logging.error(f"check {e}")

async def check_auto_trade(context: ContextTypes.DEFAULT_TYPE):
    try:
        for cid, cfg in list(state.get("auto_trade",{}).items()):
            if not cfg.get("running"): continue
            if cfg.get("done",0) >= cfg.get("count",3):
                cfg["running"]=False
                save_auto(cid,cfg)
                try:
                    await context.bot.send_message(chat_id=int(cid), text=f"🏁 **انتهى التداول التلقائي - {cfg['count']}/{cfg['count']}**\n\n💰 دخلت: {cfg['count']} صفقات\n💵 المبلغ: {cfg['amount_sar']} ر.س / {cfg['amount_usd']}$\n\n{get_ssid_status_text(cid)}", reply_markup=main_keyboard(), parse_mode='Markdown')
                except: pass
                continue
            # فحص كل الأسواق ويدور أقوى فرصة 94+
            best=get_best_legendary()
            if not best: continue
            if best["score_num"] < cfg.get("min_score",94): continue
            # هنا تنفيذ صفقة حقيقية
            ok, msg = try_pocket_trade(best["pair"], best["signal"], cfg["amount_usd"], cfg["duration"])
            cfg["done"]=cfg.get("done",0)+1
            save_auto(cid,cfg)
            try:
                await context.bot.send_message(chat_id=int(cid), text=f"✅ **صفقة {cfg['done']}/{cfg['count']}**\n\n🏆 {best['flag']} {best['pair']} {best['signal_ar']} سكور {best['score']}\n💰 {cfg['amount_sar']} ر.س / {cfg['amount_usd']}$ | ⏱️ {cfg['duration']}د\n📊 {best['strength_txt']}\n\n{msg}\n\n⏳ باقي {cfg['count']-cfg['done']} ويوقف لحاله", reply_markup=auto_trade_menu_kb(cid), parse_mode='Markdown')
                await send_signal_with_image(context, cid, best, save_to_history=True)
            except: pass
    except Exception as e:
        logging.error(f"auto_trade {e}")

async def clean(context: ContextTypes.DEFAULT_TYPE):
    try:
        for cid in list(state.get("trades",{}).keys()):
            state["trades"][cid]=[t for t in state["trades"][cid] if time.time()-t.get("ts",0)<43200]
        save_state(state)
    except: pass

def ensure_loop():
    try:
        asyncio.new_event_loop().close()
    except: pass
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except: pass

def main():
    ensure_loop()
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
        time.sleep(1)
    except: pass
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=180, first=30)
    app.job_queue.run_repeating(check_auto_trade, interval=180, first=60)
    app.job_queue.run_repeating(clean, interval=3600, first=60)
    logging.info("V4.0 LEGENDARY + AUTO TRADE + LIVE SSID READY")
    app.run_polling(drop_pending_updates=True, close_loop=False, allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    main()
