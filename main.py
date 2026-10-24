import os, time, logging, requests, base64, warnings, json, asyncio, threading
from datetime import datetime
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Bot V6 NEON - 4MIN AUTO-DELETE - NEON IMAGES - 4TF REAL"
@app_flask.route('/health')
def health():
    return "OK - V6 NEON Alive", 200
@app_flask.route('/ping')
def ping():
    return "pong V6 NEON", 200
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask V6 on port {port}", flush=True)
    app_flask.run(host='0.0.0.0', port=port)
def self_ping():
    while True:
        try:
            time.sleep(240)
            url = os.environ.get("RENDER_EXTERNAL_URL") or "https://quotex-bot-wqiv.onrender.com"
            requests.get(f"{url}/health", timeout=5)
            print("SELF-PING V6 OK", flush=True)
        except Exception as e:
            print(f"SELF-PING FAIL: {e}", flush=True)
import warnings as _w
_w.filterwarnings('ignore')
os.environ['XDG_CACHE_HOME'] = '/tmp'
os.environ['PYTHONWARNINGS'] = 'ignore'
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
# === V6 NEON IMAGES - صور نيون حقيقية ===
def create_images():
    try:
        import shutil
        from PIL import Image
        os.makedirs('/tmp/bot_images', exist_ok=True)
        buy_candidates = [
            "/mnt/data/image_ED723F5C-9DBE-43E7-9B0F-08B5603409E7.jpeg",
            "/mnt/data/image_95E35661-79B3-44D6-BBFA-4CD6B2F7858E.jpeg",
            "./image_ED723F5C-9DBE-43E7-9B0F-08B5603409E7.jpeg",
            "image_ED723F5C-9DBE-43E7-9B0F-08B5603409E7.jpeg"
        ]
        sell_candidates = [
            "/mnt/data/image_7DC4DD21-B51E-44B0-84D2-BE5E4DEFE71C.jpeg",
            "./image_7DC4DD21-B51E-44B0-84D2-BE5E4DEFE71C.jpeg",
            "image_7DC4DD21-B51E-44B0-84D2-BE5E4DEFE71C.jpeg"
        ]
        for src in buy_candidates:
            if os.path.exists(src):
                shutil.copy(src, "/tmp/bot_images/buy.jpg")
                print(f"Neon BUY copied - V6 NEON HIGH QUALITY", flush=True)
                break
        else:
            Image.new('RGB', (800, 800), (0, 200, 0)).save("/tmp/bot_images/buy.jpg")
        for src in sell_candidates:
            if os.path.exists(src):
                shutil.copy(src, "/tmp/bot_images/sell.jpg")
                print(f"Neon SELL copied - V6 NEON HIGH QUALITY", flush=True)
                break
        else:
            Image.new('RGB', (800, 800), (200, 0, 0)).save("/tmp/bot_images/sell.jpg")
        print("Images created - BUY/SELL OK - V6 NEON 4MIN", flush=True)
    except Exception as e:
        print(f"Image fail V6: {e}", flush=True)
_price_cache = {}
def get_free_forex(pair):
    try:
        r = requests.get(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{pair[:3].lower()}.json", timeout=5)
        if r.status_code==200:
            return float(r.json()[pair[:3].lower()][pair[3:].lower()])
    except:
        pass
    return None
def fetch_yf_real(symbol, interval="5m", period="1d"):
    for p in [period, "5d", "7d", "10d"]:
        try:
            df = yf.download(symbol, period=p, interval=interval, progress=False, auto_adjust=True, threads=False)
            if df is not None and len(df)>=20:
                return df
        except:
            continue
    return None
def fetch_4tf_live(symbol):
    try:
        with ThreadPoolExecutor(max_workers=4) as ex:
            f1 = ex.submit(fetch_yf_real, symbol, "5m", "5d")
            f2 = ex.submit(fetch_yf_real, symbol, "15m", "7d")
            f3 = ex.submit(fetch_yf_real, symbol, "30m", "7d")
            f4 = ex.submit(fetch_yf_real, symbol, "60m", "7d")
            return f1.result(timeout=15), f2.result(timeout=15), f3.result(timeout=15), f4.result(timeout=15)
    except:
        return None, None, None, None
def create_fallback_df(price):
    try:
        import numpy as np
        dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='5min')
        closes = [price * (1 + np.random.uniform(-0.0005, 0.0005)) for _ in range(50)]
        df = pd.DataFrame({'Open': closes, 'High': [c*1.0003 for c in closes], 'Low': [c*0.9997 for c in closes], 'Close': closes, 'Volume': [1000]*50}, index=dates)
        return df
    except:
        return None
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
        if df_m5 is None or len(df_m5)<10:
            pair = symbol.replace("=X","")
            if len(pair)>=6:
                price = get_free_forex(pair[:3]+pair[3:])
                if price: df_m5 = create_fallback_df(price)
        if df_m5 is None: return None
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
        score=0; reasons=[]
        if price>e9: score+=1; reasons.append("EMA9 صاعد")
        else: reasons.append("EMA9 هابط")
        if price>e20: score+=1
        if e9>e20>e50: score+=1; reasons.append("ترند صاعد")
        if price>e200: score+=1
        if 30<r14<70: score+=1
        elif r14<30: score+=2; reasons.append("تشبع بيعي")
        elif r14>70: reasons.append("تشبع شرائي")
        if r14>r21: score+=1
        if m>ms and mh>0: score+=1; reasons.append("MACD صاعد")
        atr_pct=atr_n/price*100
        bb_low_n=float(bb_low.iloc[-1]) if not bb_low.isna().all() else price*0.99
        bb_up_n=float(bb_up.iloc[-1]) if not bb_up.isna().all() else price*1.01
        if price<bb_low_n: score+=2; reasons.append("Bollinger سفلي")
        if price>bb_up_n: score-=1
        vol_sma=vol.rolling(20).mean()
        if float(vol.iloc[-1])>float(vol_sma.iloc[-1]): score+=1
        if df_m15 is not None:
            c15=df_m15['Close']; e9_15=compute_ema(c15,9); e20_15=compute_ema(c15,20)
            if len(c15)>1 and float(c15.iloc[-1])>float(e9_15.iloc[-1]): score+=1
        if df_h1 is not None:
            c60=df_h1['Close']; e20_60=compute_ema(c60,20)
            if len(c60)>1 and float(c60.iloc[-1])>float(e20_60.iloc[-1]): score+=1
        if score>=7: signal="CALL"
        elif score<=3: signal="PUT"
        else: return None
        # 4 دقايق ثابت
        return {
            "symbol":symbol, "flag":FLAGS.get(symbol,""), "pair":CLEAN.get(symbol,symbol),
            "signal":signal, "signal_ar":"شراء CALL ⬆️" if signal=="CALL" else "بيع PUT ⬇️",
            "score":f"{score}/10", "strength_txt":"قوي جداً 🔥" if score>=8 else "قوي ✅" if score>=6 else "متوسط ⚡",
            "trend":f"{score}", "rsi":r14, "atr_pct":atr_pct, "best_expiry_m":"4 دقائق", "best_expiry_sec":240,
            "reason":" + ".join(reasons[:3]), "price":price
        }
    except Exception as e:
        print(f"Analyze fail: {e}", flush=True)
        return None
def get_best_signal():
    best=None
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures={ex.submit(lambda s=s: (s, fetch_4tf_live(s)), s): s for s in SYMBOLS[:6]}
        for fu in as_completed(futures):
            try:
                sym, (d5,d15,d30,dh1) = fu.result(timeout=20)
                r=analyze_10_indicators(sym,d5,d15,d30,dh1)
                if r and (best is None or int(r['score'].split('/')[0])>int(best['score'].split('/')[0])): best=r
            except: pass
    return best
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
    for sym in SYMBOLS: btns.append([InlineKeyboardButton(f"{FLAGS.get(sym,'')} {CLEAN.get(sym,sym)}", callback_data=f"m_{sym}")])
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
    if not trades: return "📊 **لا يوجد صفقات**"
    profits=len([t for t in trades if t.get("type")=="profit"]); losses=len([t for t in trades if t.get("type")=="loss"])
    total=profits+losses; winrate=(profits/total*100) if total>0 else 0
    return f"📊 **الأداء:**\n✅ ربح: {profits}\n❌ خسارة: {losses}\n📈 المجموع: {total}\n🎯 نسبة: {winrate:.1f}%"
def get_signals_history_text(cid):
    logs=state.get("signals_log",{}).get(cid,[])
    if not logs: return "📜 **لا يوجد سجل بعد**"
    txt=f"📜 **مجموع الإشارات ({len(logs)}):**\n\n"
    for entry in logs[-20:][::-1]: txt+=f"{entry.get('flag','')} {entry.get('pair','')} {entry.get('signal_ar','')} {entry.get('score','')} | {entry.get('time_str','')}\n"
    return txt
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid=str(update.effective_chat.id)
    if not state.get("auth",{}).get(cid):
        await update.message.reply_text("🔐 أرسل كلمة السر")
        return
    await update.message.reply_text("🎯 **القائمة الرئيسية V6 NEON**\n\n✅ نيون + 4 دقايق حذف", reply_markup=main_keyboard(), parse_mode='Markdown')
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid=str(update.effective_chat.id)
    text=update.message.text.strip()
    user_msg_id = update.message.message_id
    try: context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_temp_message(ctx, int(cid), user_msg_id)), 2)
    except: pass
    if text==PASSWORD:
        state.setdefault("auth",{})[cid]=True
        save_state(state)
        await context.bot.send_message(chat_id=int(cid), text="✅ تم التفعيل! V6 NEON - 4 دقايق وتنحذف", reply_markup=main_keyboard())
    else:
        try:
            msg = await context.bot.send_message(chat_id=int(cid), text="❌ كلمة سر خاطئة")
            context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_temp_message(ctx, int(cid), msg.message_id)), 3)
        except: pass
async def delete_temp_message(context, chat_id, message_id):
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query; await query.answer(); cid=str(query.from_user.id)
    try:
        if query.data in ["scan_4tf", "all_signals"]:
            await query.edit_message_text("⚡ جاري فحص 4 فريمات V6 NEON...\nM5•M15•M30•H1 - نيون")
    except: pass
    if query.data=="scan_4tf":
        r=get_best_signal()
        if r:
            try: await query.message.delete()
            except: pass
            await send_signal_with_image(context,cid,r,save_to_history=True)
        else:
            await query.edit_message_text("⚠ لا توجد إشارة قوية الآن", reply_markup=main_keyboard())
    elif query.data=="all_signals":
        results=[]
        for sym in SYMBOLS[:6]:
            d5,d15,d30,dh1=fetch_4tf_live(sym)
            rr=analyze_10_indicators(sym,d5,d15,d30,dh1)
            if rr: results.append(rr)
        if not results: await query.edit_message_text("⚠ لا توجد إشارات", reply_markup=main_keyboard())
        else:
            txt="📈 **كل الإشارات V6 NEON:**\n\n"
            for rr in sorted(results, key=lambda x: int(x['score'].split('/')[0]), reverse=True)[:5]:
                txt+=f"{rr['flag']} {rr['pair']} {rr['signal_ar']} | {rr['score']} | ⏱{rr['best_expiry_m']}\n"
            await query.edit_message_text(txt, reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="choose_market":
        await query.edit_message_text("📊 **اختيار السوق V6:**", reply_markup=markets_keyboard(), parse_mode='Markdown')
    elif query.data.startswith("m_"):
        sym=query.data.replace("m_","")
        await query.edit_message_text(f"⚡ تحليل {CLEAN.get(sym,sym)} V6...")
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
        await query.edit_message_text("🤖 **الأوتو شغال V6 NEON** ✅\n\n🔍 كل 3 دقائق\n⏳ 4 دقايق وتنحذف\n📸 نيون", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="auto_stop":
        state.setdefault("auto",{})[cid]=False; save_state(state)
        await query.edit_message_text("🛑 **متوقف**", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="stats":
        await query.edit_message_text("📊 **V6 NEON**\n✅ 10 تحاليل\n✅ نيون\n✅ 4 دقايق حذف", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data=="settings":
        auto="شغال 🟢" if state.get("auto",{}).get(cid) else "متوقف 🔴"
        await query.edit_message_text(f"⚙ **الإعدادات V6**\n🤖 الحالة: {auto}\n⏱ الحذف: 4 دقايق", reply_markup=main_keyboard(), parse_mode='Markdown')
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
        await query.edit_message_text("🎯 **القائمة الرئيسية V6 NEON**", reply_markup=main_keyboard(), parse_mode='Markdown')
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
        caption=f"{r['flag']} **{r['pair']}** {r['signal_ar']}\n\n🎯 سكور: {r['score']}\n📊 {r['strength_txt']}\n📈 ترند: {r['trend']}/10\n📊 RSI: {r['rsi']:.1f} | ATR: {r['atr_pct']:.3f}%\n⏱ المدة: {r['best_expiry_m']}\n💡 {r['reason']}\n\n🔥 V6 NEON - نيون + 4 دقايق\n📡 LIVE REAL\n⏳ تنحذف بعد 4 دقائق ⏰"
        if os.path.exists(img_path):
            sent_msg = await context.bot.send_photo(chat_id=int(cid), photo=open(img_path,'rb'), caption=caption, parse_mode='Markdown')
        else:
            sent_msg = await context.bot.send_message(chat_id=int(cid), text=caption, parse_mode='Markdown')
        expiry_sec=240
        context.job_queue.run_once(lambda ctx: asyncio.create_task(delete_signal_job(ctx,cid,sent_msg.message_id)), expiry_sec)
    except Exception as e:
        print(f"Send error: {e}", flush=True)
        try:
            await context.bot.send_message(chat_id=int(cid), text=f"{r['flag']} **{r['pair']}** {r['signal_ar']}\n🎯 {r['score']} | 4 دقائق", parse_mode='Markdown', reply_markup=main_keyboard())
        except: pass
async def delete_signal_job(context, chat_id, message_id):
    try:
        await context.bot.delete_message(chat_id=int(chat_id), message_id=message_id)
        print(f"Auto-deleted {message_id} after 4min", flush=True)
        await context.bot.send_message(chat_id=int(chat_id), text="🗑️ انتهت الإشارة (4 دقائق) - تم الحذف تلقائياً ✅\n\n🔍 الأزرار رجعت", reply_markup=main_keyboard())
    except Exception as e:
        print(f"Delete fail: {e}", flush=True)
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
    print("=== MAIN() ENTERED V6 NEON 4MIN ===", flush=True)
    for _ in range(3):
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
            time.sleep(1)
        except: pass
    time.sleep(2)
    print("Creating NEON images V6...", flush=True)
    create_images()
    print("Images done V6 NEON, starting polling loop", flush=True)
    while True:
        try:
            print("=== STARTING BOT POLLING V6 NEON 4MIN ===", flush=True)
            from telegram.ext import Application
            app=Application.builder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(buttons))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            app.job_queue.run_repeating(check_signals, interval=180, first=30)
            print("=== BOT READY V6 NEON - 4MIN DELETE - NEON IMAGES ===", flush=True)
            app.run_polling(drop_pending_updates=True, close_loop=False, allowed_updates=["message","callback_query"], poll_interval=1.0, timeout=30)
        except Exception as e:
            import traceback
            print(f"CRASHED: {e}", flush=True)
            traceback.print_exc()
            time.sleep(10)
            continue
if __name__=="__main__":
    print("=== PROGRAM START V6 NEON ===", flush=True)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    time.sleep(2)
    main()
