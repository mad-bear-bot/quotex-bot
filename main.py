import os, logging, json
import yfinance as yf
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PASSWORD = "7154"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "AUDUSD=X", "GBPJPY=X"]
NAMES = {"EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "EURJPY=X":"EUR/JPY", "AUDUSD=X":"AUD/USD", "GBPJPY=X":"GBP/JPY"}

# تخزين بسيط
STATE_FILE = "/tmp/bot_state.json"
def load_state():
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return {"auth": {}, "sent": {}}
def save_state(s):
    try:
        with open(STATE_FILE,'w') as f: json.dump(s,f)
    except: pass

state = load_state()
sent_pairs = state.get("sent", {})

logging.basicConfig(level=logging.INFO)

def analyze_smc(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df) < 50: return None
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        # اصلاح التحذير - استخدام .item()
        last_close = float(closes[-1].item() if hasattr(closes[-1], 'item') else closes[-1])
        prev_high = float(highs[-20:-1].max())
        prev_low = float(lows[-20:-1].min())
        
        bullish_bos = last_close > prev_high
        bearish_bos = last_close < prev_low
        # Order Block بسيط
        ob_bullish = len(closes)>5 and closes[-1] > closes[-2] and lows[-3] < lows[-4]
        ob_bearish = len(closes)>5 and closes[-1] < closes[-2] and highs[-3] > highs[-4]

        signal = None; conf=0
        if bullish_bos and ob_bullish: signal, conf = "CALL ⬆️", 85
        elif bearish_bos and ob_bearish: signal, conf = "PUT ⬇️", 85
        elif bullish_bos: signal, conf = "CALL ⬆️", 70
        elif bearish_bos: signal, conf = "PUT ⬇️", 70
            
        if signal:
            clean = NAMES.get(symbol, symbol.replace("=X",""))
            reason = []
            if bullish_bos or bearish_bos: reason.append("BOS " + ("صاعد" if bullish_bos else "هابط"))
            if ob_bullish or ob_bearish: reason.append("Order Block")
            return {"pair": clean, "symbol": symbol, "signal": signal, "conf": conf, "price": last_close, "reason": " + ".join(reason), "time": datetime.now().strftime("%H:%M")}
        return None
    except Exception as e:
        logging.error(f"Analyze {symbol}: {e}")
        return None

def is_authed(chat_id):
    return str(chat_id) in state.get("auth", {}) and state["auth"][str(chat_id)]

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 تحليل الآن", callback_data="analyze"), InlineKeyboardButton("📈 الحالة", callback_data="status")],
        [InlineKeyboardButton("⏸️ إيقاف الإشارات", callback_data="pause"), InlineKeyboardButton("▶️ تشغيل الإشارات", callback_data="resume")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if is_authed(chat_id):
        await update.message.reply_text("✅ انت مسجل دخول already\nنظام SMC شغال...", reply_markup=main_keyboard())
    else:
        await update.message.reply_text("🔐 مرحبا في MAD.BEAR.BOT 🐻\nأرسل الرقم السري للدخول:\n`7154`", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state
    text = update.message.text.strip()
    chat_id = str(update.effective_chat.id)
    
    if text == BOT_PASSWORD:
        if "auth" not in state: state["auth"] = {}
        state["auth"][chat_id] = True
        save_state(state)
        await update.message.reply_text(
            "✅ تم فتح البوت بنجاح!\n\n"
            "🔥 نظام SMC الحقيقي شغال الآن\n"
            "📊 BOS + Order Block\n"
            "⏰ M5 - دخول 3M\n"
            "💹 سوق حقيقي (بدون OTC)\n\n"
            "استخدم الأزرار بالأسفل 👇",
            reply_markup=main_keyboard()
        )
        return
    
    if is_authed(chat_id):
        await update.message.reply_text("👀 البوت يفحص السوق كل دقيقة...\nاضغط تحليل الآن للفحص الفوري", reply_markup=main_keyboard())
    else:
        await update.message.reply_text("❌ الرقم السري غلط! أرسل `7154`", parse_mode="Markdown")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state, sent_pairs
    query = update.callback_query
    await query.answer()
    chat_id = str(query.from_user.id)
    
    if not is_authed(chat_id):
        await query.edit_message_text("❌ غير مسجل! أرسل 7154 أولاً")
        return

    if query.data == "analyze":
        await query.edit_message_text("🔍 جاري فحص 6 أزواج...")
        found = 0
        for sym in SYMBOLS:
            r = analyze_smc(sym)
            if r:
                found += 1
                msg = f"""📊 {r['pair']} - سوق حقيقي
{r['signal']} - مدة 3M

💰 السعر: {r['price']:.5f}
📈 التحليل: {r['reason']}
🎯 الثقة: {r['conf']}%
⏰ الوقت: {r['time']}"""
                await context.bot.send_message(chat_id=chat_id, text=msg)
        if found==0:
            await context.bot.send_message(chat_id=chat_id, text="⚪ لا يوجد إشارات حالياً - السوق في تجميع\nسأفحص مرة أخرى بعد دقيقة", reply_markup=main_keyboard())
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"✅ تم إرسال {found} إشارات", reply_markup=main_keyboard())
            
    elif query.data == "status":
        await query.edit_message_text(f"📈 الحالة:\n✅ البوت شغال\n🔍 يفحص كل 60 ثانية\n💹 {len(SYMBOLS)} أزواج\n⏰ {datetime.now().strftime('%H:%M:%S')}", reply_markup=main_keyboard())
    elif query.data == "pause":
        state["auth"][chat_id] = False
        save_state(state)
        await query.edit_message_text("⏸️ تم إيقاف الإشارات التلقائية\nاضغط تشغيل لإعادة التشغيل", reply_markup=main_keyboard())
        state["auth"][chat_id] = True  # نبقيه مسجل لكن نوقف الـ job لاحقا
    elif query.data == "resume":
        state["auth"][chat_id] = True
        save_state(state)
        await query.edit_message_text("▶️ تم تشغيل الإشارات ✅", reply_markup=main_keyboard())

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global sent_pairs, state
    import time
    for chat_id, ok in list(state.get("auth", {}).items()):
        if not ok: continue
        for symbol in SYMBOLS:
            try:
                r = analyze_smc(symbol)
                if r:
                    last = sent_pairs.get(r['pair'], 0)
                    if time.time() - last < 600: continue
                    msg = f"""📊 {r['pair']} - سوق حقيقي
{r['signal']} - مدة 3M

💰 السعر: {r['price']:.5f}
📈 {r['reason']} | 🎯 {r['conf']}%
⏰ {r['time']}"""
                    await context.bot.send_message(chat_id=int(chat_id), text=msg)
                    sent_pairs[r['pair']] = time.time()
                    state["sent"] = sent_pairs
                    save_state(state)
            except Exception as e:
                logging.error(e)

# Flask for Render port
flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return "MAD.BEAR.BOT is running - password 7154"
def run_flask():
    port = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing"); return
    Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=60, first=15)
    logging.info("MAD BEAR V4 with buttons - password 7154")
    app.run_polling()

if __name__ == "__main__":
    main()
