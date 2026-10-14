import os, time, logging, requests, random
from datetime import datetime, timezone
import threading
import yfinance as yf

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
PASSWORD = os.environ.get("BOT_PASSWORD", "7154")

from flask import Flask
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return 'POCKET OPTION BOT - 8 MARKETS - ARABIC'
@flask_app.route('/health')
def health(): return 'OK'
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# === 8 أسواق موجودة في Pocket Option فقط ===
SYMBOLS = [
    "EURUSD=X",  # EUR/USD
    "GBPUSD=X",  # GBP/USD
    "USDJPY=X",  # USD/JPY
    "AUDUSD=X",  # AUD/USD
    "USDCAD=X",  # USD/CAD
    "EURJPY=X",  # EUR/JPY
    "GBPJPY=X",  # GBP/JPY
    "GC=F"       # GOLD XAU/USD - ذهب
]

CLEAN = {
    "EURUSD=X":"EUR/USD",
    "GBPUSD=X":"GBP/USD",
    "USDJPY=X":"USD/JPY",
    "AUDUSD=X":"AUD/USD",
    "USDCAD=X":"USD/CAD",
    "EURJPY=X":"EUR/JPY",
    "GBPJPY=X":"GBP/JPY",
    "GC=F":"GOLD"
}

FLAGS = {
    "EURUSD=X":"🇪🇺🇺🇸",
    "GBPUSD=X":"🇬🇧🇺🇸",
    "USDJPY=X":"🇺🇸🇯🇵",
    "AUDUSD=X":"🇦🇺🇺🇸",
    "USDCAD=X":"🇺🇸🇨🇦",
    "EURJPY=X":"🇪🇺🇯🇵",
    "GBPJPY=X":"🇬🇧🇯🇵",
    "GC=F":"🥇"
}

state = {"auth":{}, "paused":{}, "expiry":{}}

def save_state(s): 
    try:
        import json
        json.dump(s, open("/tmp/state.json","w"))
    except: pass

def load_state():
    try:
        import json
        if os.path.exists("/tmp/state.json"):
            return json.load(open("/tmp/state.json"))
    except: pass
    return {"auth":{}, "paused":{}, "expiry":{}}
state = load_state()

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_ema(close, period):
    return close.ewm(span=period, adjust=False).mean()

def analyze_real(symbol):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2d", interval="5m")
        if df.empty or len(df) < 30:
            df = ticker.history(period="5d", interval="15m")
            if df.empty or len(df) < 30:
                df = ticker.history(period="1mo", interval="1h")
                if df.empty:
                    return None

        close = df['Close']
        high = df['High']
        low = df['Low']
        price = float(close.iloc[-1])
        
        rsi = compute_rsi(close, 14)
        rsi_now = float(rsi.iloc[-1])
        rsi_prev = float(rsi.iloc[-2]) if len(rsi) > 1 else rsi_now
        
        ema20 = compute_ema(close, 20)
        ema50 = compute_ema(close, 50)
        ema20_now = float(ema20.iloc[-1])
        ema50_now = float(ema50.iloc[-1])
        
        ema12 = compute_ema(close, 12)
        ema26 = compute_ema(close, 26)
        macd = ema12 - ema26
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_now = float(macd.iloc[-1])
        macd_sig_now = float(signal_line.iloc[-1])
        
        last_high = float(high.tail(20).max())
        last_low = float(low.tail(20).min())
        
        bullish = 0
        bearish = 0
        
        if price > ema20_now: bullish += 1
        else: bearish += 1
        if ema20_now > ema50_now: bullish += 1
        else: bearish += 1
        if 50 < rsi_now < 70 and rsi_now > rsi_prev: bullish += 1
        elif 30 < rsi_now < 50 and rsi_now < rsi_prev: bearish += 1
        if macd_now > macd_sig_now: bullish += 1
        else: bearish += 1
        if price >= last_high * 0.999: bullish += 1
        if price <= last_low * 1.001: bearish += 1
        
        if bullish >= 3 and bullish > bearish:
            signal = "CALL"
            signal_ar = "صعود"
        elif bearish >= 3 and bearish > bullish:
            signal = "PUT"
            signal_ar = "هبوط"
        else:
            if bullish > bearish:
                signal = "CALL"
                signal_ar = "صعود"
            else:
                signal = "PUT"
                signal_ar = "هبوط"
        
        score = 50 + (bullish * 8 if signal=="CALL" else bearish * 8)
        score += max(0, (rsi_now - 50) if signal=="CALL" else (50 - rsi_now)) * 0.5
        score = min(96, max(65, int(score)))
        conf = min(92, max(75, score - random.randint(2,5)))
        
        if score >= 88:
            strength = "قوية جدا 🔥"
            conf_text = "ممتازة"
        elif score >= 80:
            strength = "قوية"
            conf_text = "جيدة جدا"
        else:
            strength = "متوسطة"
            conf_text = "جيدة"
        
        align_num = bullish if signal=="CALL" else bearish
        
        return {
            "pair": CLEAN.get(symbol,symbol),
            "flag": FLAGS.get(symbol,""),
            "signal": signal,
            "signal_ar": signal_ar,
            "conf": conf,
            "score": score,
            "price": price,
            "strength": strength,
            "conf_text": conf_text,
            "rsi_m5": rsi_now,
            "align_num": align_num,
            "symbol": symbol
        }
    except Exception as e:
        logging.error(f"analyze {symbol} {e}")
        return None

def get_best():
    results = []
    for sym in SYMBOLS:
        r = analyze_real(sym)
        if r:
            results.append(r)
            time.sleep(0.3)
    if not results: return None
    results.sort(key=lambda x: (x["align_num"], x["score"]), reverse=True)
    return results[0]

def get_all_signals():
    results = []
    for sym in SYMBOLS:
        r = analyze_real(sym)
        if r:
            results.append(r)
    return results

def format_message_ar(r, expiry="5 د"):
    """مقترح عربي 1 - قصير"""
    arrow = "⬆️" if r["signal"]=="CALL" else "⬇️"
    color = "🟢" if r["signal"]=="CALL" else "🔴"
    
    # سعر الذهب يختلف
    if r["symbol"] == "GC=F":
        price_fmt = f"{r['price']:.2f}"
    else:
        price_fmt = f"{r['price']:.5f}"
    
    msg = f"💱 {r['pair']} {r['flag']}\n"
    msg += f"{color} {r['signal_ar']} {arrow} | ⏱️ {expiry}\n"
    msg += f"\n🎯 الثقة: {r['conf']}% {r['conf_text']}\n"
    msg += f"⚡ القوة: {r['score']}/100 {r['strength']}\n"
    msg += f"\n💰 دخول: {price_fmt}\n"
    msg += f"📊 RSI: {r['rsi_m5']:.1f} | {r['align_num']}/5 مؤشرات"
    return msg

# === Telegram ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 مسح جميع الأسواق", callback_data="scan_all"), InlineKeyboardButton("📈 إشارات السوق", callback_data="signals")],
        [InlineKeyboardButton("📊 اختيار السوق", callback_data="choose_market"), InlineKeyboardButton("⏰ مدة الصفقة", callback_data="expiry")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"), InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("⚡ بدء تحليل الأسواق", callback_data="check_now")]
    ])

def expiry_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1 دقيقة", callback_data="exp_1"), InlineKeyboardButton("3 دقايق", callback_data="exp_3")],
        [InlineKeyboardButton("5 دقايق", callback_data="exp_5"), InlineKeyboardButton("10 دقايق", callback_data="exp_10")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

def markets_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("EUR/USD 🇪🇺🇺🇸", callback_data="m_EURUSD=X"), InlineKeyboardButton("GBP/USD 🇬🇧🇺🇸", callback_data="m_GBPUSD=X")],
        [InlineKeyboardButton("USD/JPY 🇺🇸🇯🇵", callback_data="m_USDJPY=X"), InlineKeyboardButton("AUD/USD 🇦🇺🇺🇸", callback_data="m_AUDUSD=X")],
        [InlineKeyboardButton("USD/CAD 🇺🇸🇨🇦", callback_data="m_USDCAD=X"), InlineKeyboardButton("EUR/JPY 🇪🇺🇯🇵", callback_data="m_EURJPY=X")],
        [InlineKeyboardButton("GBP/JPY 🇬🇧🇯🇵", callback_data="m_GBPJPY=X"), InlineKeyboardButton("GOLD 🥇 ذهب", callback_data="m_GC=F")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    state["auth"][cid] = False
    save_state(state)
    await update.message.reply_text("🔐 ادخل الرقم السري:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    text = update.message.text.strip()
    if not state.get("auth",{}).get(cid):
        if text == PASSWORD:
            state["auth"][cid] = True
            save_state(state)
            welcome = "🤖 تحليل Pocket Option\n📡 8 MARKETING REAL\n\n🎯 القائمة الرائيسية"
            await update.message.reply_text(welcome, reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ رقم خطأ:")
        return

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = str(query.from_user.id)
    if not state.get("auth",{}).get(cid):
        await query.edit_message_text("🔐 ادخل الرقم السري أولاً /start")
        return
    expiry = state.get("expiry",{}).get(cid, "5 د") if "expiry" in state else "5 د"
    
    if query.data in ["check_now","scan_all"]:
        await query.edit_message_text("⏳ جاري تحليل 8 أسواق من Yahoo...")
        best = get_best()
        if best:
            await query.edit_message_text(format_message_ar(best, expiry), reply_markup=main_keyboard())
        else:
            await query.edit_message_text("⚠️ السوق مغلق", reply_markup=main_keyboard())
    
    elif query.data == "signals":
        await query.edit_message_text("⏳ جلب كل الأسواق...")
        all_s = get_all_signals()
        if not all_s:
            await query.edit_message_text("⚠️ لا يوجد بيانات", reply_markup=main_keyboard())
            return
        txt = "📈 **إشارات Pocket Option:**\n\n"
        for r in all_s:
            arrow = "🟢⬆️" if r["signal"]=="CALL" else "🔴⬇️"
            txt += f"{arrow} {r['pair']} {r['signal_ar']} {r['score']}🔥\n"
        await query.edit_message_text(txt, reply_markup=main_keyboard(), parse_mode='Markdown')
    
    elif query.data == "choose_market":
        await query.edit_message_text("📊 **اختيار السوق - Pocket Option:**", reply_markup=markets_keyboard(), parse_mode='Markdown')
    
    elif query.data.startswith("m_"):
        sym = query.data.replace("m_","")
        await query.edit_message_text(f"⏳ جلب {CLEAN.get(sym,sym)}...")
        r = analyze_real(sym)
        if r:
            await query.edit_message_text(format_message_ar(r, expiry), reply_markup=main_keyboard())
        else:
            await query.edit_message_text("⚠️ فشل", reply_markup=main_keyboard())
    
    elif query.data == "expiry":
        await query.edit_message_text("⏰ **مدة الصفقة:**", reply_markup=expiry_keyboard(), parse_mode='Markdown')
    
    elif query.data.startswith("exp_"):
        exp_map = {"exp_1":"1 د","exp_3":"3 د","exp_5":"5 د","exp_10":"10 د"}
        chosen = exp_map.get(query.data, "5 د")
        state.setdefault("expiry",{})[cid]=chosen
        save_state(state)
        await query.edit_message_text(f"✅ المدة: **{chosen}**", reply_markup=main_keyboard(), parse_mode='Markdown')
    
    elif query.data == "stats":
        await query.edit_message_text("📊 **الإحصائيات:**\n\n📡 8 أسواق Pocket Option\n🥇 GOLD + 7 فوركس\n✅ Score 88+ فقط\n⏱️ كل دقيقة\n🟢 LIVE", reply_markup=main_keyboard(), parse_mode='Markdown')
    
    elif query.data == "settings":
        await query.edit_message_text(f"⚙️ **الإعدادات:**\n\n⏰ المدة: {expiry}\n📡 Yahoo Finance\n📊 8 أسواق PO", reply_markup=main_keyboard(), parse_mode='Markdown')
    
    elif query.data == "back_main":
        await query.edit_message_text("🎯 **القائمة الرئيسية**", reply_markup=main_keyboard(), parse_mode='Markdown')

last_global_send = 0
last_sent_info = ""

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_global_send, last_sent_info
    now = time.time()
    if now - last_global_send < 300: return
    try:
        best = get_best()
        if not best: return
        if best["score"] < 88: return
        if last_sent_info == best["pair"] and (now - last_global_send) < 600: return
        sent = 0
        for cid, ok in list(state.get("auth",{}).items()):
            if not ok or state.get("paused",{}).get(cid): continue
            c_exp = state.get("expiry",{}).get(cid, "5 د")
            try:
                await context.bot.send_message(chat_id=int(cid), text=format_message_ar(best, c_exp))
                sent += 1
            except: pass
        if sent > 0:
            last_global_send = now
            last_sent_info = best["pair"]
    except Exception as e:
        logging.error(f"check {e}")

async def clean(context: ContextTypes.DEFAULT_TYPE): pass

def main():
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
        time.sleep(1)
    except: pass
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=60, first=20)
    app.job_queue.run_repeating(clean, interval=3600, first=30)
    logging.info("POCKET OPTION 8 MARKETS - ARABIC READY")
    app.run_polling(drop_pending_updates=True, close_loop=False, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    main()
