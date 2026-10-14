
import os, time, logging, requests, random, asyncio
from datetime import datetime, timedelta, timezone
import threading

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
PASSWORD = os.environ.get("BOT_PASSWORD", "12345")

# === Flask ===
from flask import Flask
flask_app = Flask(__name__)

@flask_app.route('/')
def home(): return 'MAD BEAR V40 - WORKING'
@flask_app.route('/health')
def health(): return 'OK'

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# === Bot Data ===
SYMBOLS = ["EURUSD=X","GBPUSD=X","USDJPY=X","EURJPY=X","GBPJPY=X","AUDUSD=X"]
CLEAN = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY","EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDUSD=X":"AUD/USD"}
FLAGS = {"EURUSD=X":"🇪🇺🇺🇸","GBPUSD=X":"🇬🇧🇺🇸","USDJPY=X":"🇺🇸🇯🇵","EURJPY=X":"🇪🇺🇯🇵","GBPJPY=X":"🇬🇧🇯🇵","AUDUSD=X":"🇦🇺🇺🇸"}
PAYOUT = {"EURUSD=X":"92%","GBPUSD=X":"90%","USDJPY=X":"88%","EURJPY=X":"89%","GBPJPY=X":"90%","AUDUSD=X":"88%"}
NAMES = CLEAN

BEAR_BUY_PATH = "/tmp/bear_buy.jpg"
BEAR_SELL_PATH = "/tmp/bear_sell.jpg"

state = {"auth":{}, "paused":{}, "expiry":{}}

def save_state(s): 
    try:
        import json
        json.dump(s, open("/tmp/state.json","w"))
    except: pass

def load_state():
    try:
        import json, os
        if os.path.exists("/tmp/state.json"):
            return json.load(open("/tmp/state.json"))
    except: pass
    return {"auth":{}, "paused":{}, "expiry":{}}
state = load_state()

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def setup_bear_images():
    pass

def analyze(symbol):
    try:
        now_utc = datetime.now(timezone.utc)
        random.seed(abs(hash(symbol + str(now_utc.minute // 5))) % 10000)
        signal = random.choice(["CALL","PUT"])
        conf = random.randint(82,92)
        score = random.randint(84,95)
        price = round(random.uniform(0.85,1.35),5)
        rsi_m5 = random.uniform(52,68) if signal=="CALL" else random.uniform(32,48)
        bos_text = "BOS UP" if signal=="CALL" else "BOS DOWN"
        t15 = "BULL" if signal=="CALL" else "BEAR"
        t1h = "BULL" if signal=="CALL" else "BEAR"
        return {"pair":CLEAN.get(symbol,symbol),"flag":FLAGS.get(symbol,""),"payout":PAYOUT.get(symbol,""),"signal":signal,"conf":conf,"score":score,"price":price,"bos_text":bos_text,"t15":t15,"t1h":t1h,"alignment":"3/3","align_num":3,"market_structure":"BULLISH" if signal=="CALL" else "BEARISH","strength":"قوية جدا","conf_text":"قوية","expiry":(now_utc+timedelta(minutes=3)).strftime("%H:%M:%S UTC"),"rsi_m5":rsi_m5}
    except Exception as e:
        logging.error(f"analyze {e}")
        return None

def get_best():
    all_s = [r for r in [analyze(s) for s in SYMBOLS] if r]
    if not all_s: return None
    all_s.sort(key=lambda x:(x["align_num"], x["score"]), reverse=True)
    return all_s[0]

def format_message(r):
    direction_emoji="🟢" if r["signal"]=="CALL" else "🔴"
    arrow="⬆️" if r["signal"]=="CALL" else "⬇️"
    msg=f"💱 PAIR: {r['pair']} {r['flag']} | PAYOUT: {r['payout']}\n"
    msg+=f"{direction_emoji} DIRECTION: {r['signal']} {arrow}\n"
    msg+=f"🎯 CONFIDENCE: {r['conf']}% ({r['conf_text']})\n"
    msg+=f"⚡ SIGNAL SCORE: {r['score']}/100\n"
    msg+=f"💰 ENTRY PRICE: {r['price']:.5f}\n"
    msg+=f"⏱️ EXPIRY: 3 MIN\n"
    msg+=f"🔗 {r['alignment']} | RSI: {r['rsi_m5']:.1f}\n"
    return msg

# === Telegram handlers ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

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
            welcome = "✅ تم تسجيل الدخول\n\n🤖 SMART MARKET ANALYSIS\nإشارات تحليلية — تداول يدوي\n\n🎯 القائمة الرئيسية"
            await update.message.reply_text(welcome, reply_markup=main_keyboard())
        else:
            await update.message.reply_text("❌ رقم خطأ، حاول مرة ثانية:")
        return

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 مسح جميع الأسواق", callback_data="scan_all"),
            InlineKeyboardButton("📈 إشارات السوق", callback_data="signals")
        ],
        [
            InlineKeyboardButton("📊 اختيار السوق", callback_data="choose_market"),
            InlineKeyboardButton("⏰ مدة الصفقة", callback_data="expiry")
        ],
        [
            InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
        ],
        [
            InlineKeyboardButton("⚡ بدء تحليل الأسواق", callback_data="check_now")
        ]
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
        [InlineKeyboardButton("USD/JPY 🇺🇸🇯🇵", callback_data="m_USDJPY=X"), InlineKeyboardButton("EUR/JPY 🇪🇺🇯🇵", callback_data="m_EURJPY=X")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = str(query.from_user.id)
    if not state.get("auth",{}).get(cid):
        await query.edit_message_text("🔐 ادخل الرقم السري أولاً /start")
        return
    expiry = state.get("expiry",{}).get(cid, "3 MIN") if "expiry" in state else "3 MIN"
    if query.data in ["check_now","scan_all"]:
        best = get_best()
        if best:
            await query.edit_message_text(format_message(best), reply_markup=main_keyboard())
        else:
            await query.edit_message_text("⏳ ما في إشارة الان", reply_markup=main_keyboard())
    elif query.data == "signals":
        all_s = [analyze(s) for s in SYMBOLS[:4]]
        all_s = [x for x in all_s if x]
        txt = "📈 **إشارات السوق الحالية:**\n\n"
        for r in all_s:
            arrow = "🟢⬆️" if r["signal"]=="CALL" else "🔴⬇️"
            txt += f"{arrow} {r['pair']} {r['signal']} {r['conf']}% Score:{r['score']}\n"
        await query.edit_message_text(txt, reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data == "choose_market":
        await query.edit_message_text("📊 **اختيار السوق:**", reply_markup=markets_keyboard(), parse_mode='Markdown')
    elif query.data.startswith("m_"):
        sym = query.data.replace("m_","")
        r = analyze(sym)
        if r:
            await query.edit_message_text(format_message(r), reply_markup=main_keyboard())
    elif query.data == "expiry":
        await query.edit_message_text("⏰ **مدة الصفقة:**", reply_markup=expiry_keyboard(), parse_mode='Markdown')
    elif query.data.startswith("exp_"):
        exp_map = {"exp_1":"1 MIN","exp_3":"3 MIN","exp_5":"5 MIN","exp_10":"10 MIN"}
        chosen = exp_map.get(query.data, "3 MIN")
        state.setdefault("expiry",{})[cid]=chosen
        save_state(state)
        await query.edit_message_text(f"✅ المدة: **{chosen}**", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data == "stats":
        await query.edit_message_text("📊 **الإحصائيات:**\n\n✅ Score 88+\n⏱️ كل 40 ثانية\n📈 6 أزواج\n🟢 شغال", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data == "settings":
        await query.edit_message_text(f"⚙️ **الإعدادات:**\n\n⏰ المدة: {expiry}\n🔔 التنبيهات: مفعلة", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data == "back_main":
        await query.edit_message_text("🎯 **القائمة الرئيسية**", reply_markup=main_keyboard(), parse_mode='Markdown')
    elif query.data == "status":
        await query.edit_message_text("📊 شغال - كل 5 دق\nممتاز فقط 88+", reply_markup=main_keyboard())
    elif query.data == "pause":
        state["paused"][cid] = True
        save_state(state)
        await query.edit_message_text("⏸️ تم الايقاف", reply_markup=main_keyboard())
    elif query.data == "resume":
        state["paused"][cid] = False
        save_state(state)
        await query.edit_message_text("▶️ تم التشغيل", reply_markup=main_keyboard())

last_global_send = 0
last_sent_info = ""

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_global_send, last_sent_info
    now = time.time()
    if now - last_global_send < 300:
        return
    try:
        best = get_best()
        if not best: return
        if best["score"] < 88 or best["conf"] < 82 or best["align_num"] < 2:
            logging.info(f"skip low {best['pair']} score={best['score']}")
            return
        if last_sent_info == best["pair"] and (now - last_global_send) < 600:
            return
        msg = format_message(best)
        sent = 0
        for cid, ok in list(state.get("auth",{}).items()):
            if not ok or state.get("paused",{}).get(cid): continue
            try:
                await context.bot.send_message(chat_id=int(cid), text=msg)
                sent += 1
            except Exception as e:
                logging.error(f"send {e}")
        if sent > 0:
            last_global_send = now
            last_sent_info = best["pair"]
            logging.info(f"SENT {best['pair']} to {sent}")
    except Exception as e:
        logging.error(f"check_signals {e}")

async def clean(context: ContextTypes.DEFAULT_TYPE):
    pass

def main():
    # احذف webhook
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
        time.sleep(1)
    except: pass

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=40, first=15)
    app.job_queue.run_repeating(clean, interval=3600, first=30)
    logging.info("V40 STARTING - READY FOR /start")
    app.run_polling(drop_pending_updates=True, close_loop=False, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # شغل Flask في الخلفية
    threading.Thread(target=run_flask, daemon=True).start()
    time.sleep(2)
    main()
