
import os, time, logging, requests
from flask import Flask
import threading

flask_app = Flask(__name__)
@flask_app.route('/')
def home(): return 'V28 FULL - FIXED NameError - 5MIN NO HEADER'
@flask_app.route('/health')
def health(): return 'OK'
def run_flask():
    flask_app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(2)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
try:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
    time.sleep(1)
except: pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# استيراد التحليل
from main_V23_FINAL import analyze, format_message, setup_bear_images, BEAR_BUY_PATH, BEAR_SELL_PATH, SYMBOLS, state, CLEAN_MODE, BEAR_IMAGES_SETUP

logging.basicConfig(level=logging.INFO)
last_trade_end = {}

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_trade_end
    now = time.time()
    for cid, ok in list(state.get("auth",{}).items()):
        if not ok or state.get("paused",{}).get(cid): continue
        if cid in last_trade_end:
            if now - last_trade_end[cid] < 300: continue
        try:
            all_signals=[]
            for s in SYMBOLS:
                try:
                    r=analyze(s)
                    if r: all_signals.append(r)
                except: pass
            if not all_signals: continue
            strong = [r for r in all_signals if r.get("align_num")==3 and r.get("score",0)>=82 and r.get("conf",0)>=78]
            if not strong: continue
            strong.sort(key=lambda x:(x["score"],x["conf"]),reverse=True)
            best = strong[0]
            msg=format_message(best)
            setup_bear_images()
            img=BEAR_BUY_PATH if best["signal"]=="CALL" else BEAR_SELL_PATH
            try:
                if os.path.exists(img):
                    await context.bot.send_photo(chat_id=int(cid),photo=open(img,"rb"),caption=f"{msg}")
                else:
                    await context.bot.send_message(chat_id=int(cid),text=f"{msg}")
            except:
                await context.bot.send_message(chat_id=int(cid),text=f"{msg}")
            last_trade_end[cid]=now
            logging.info(f"V28 sent {best['pair']} to {cid}")
        except Exception as e:
            logging.error(f"auto error {e}")

# ===== Handlers الاصلية من V23 =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    cid=str(update.effective_chat.id)
    if is_authed(cid):
        await context.bot.send_message(chat_id=cid, text="🐻 MAD BEAR V23\n\n✅ القائمة الرئيسية", reply_markup=main_keyboard())
    else: await context.bot.send_message(chat_id=cid, text="🐻 MAD BEAR\n\n🔐 أرسل الرقم السري:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state
    text=update.message.text.strip(); cid=str(update.effective_chat.id)
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    if text==BOT_PASSWORD:
        state["auth"][cid]=True; save_state(state)
        await context.bot.send_message(chat_id=cid, text="تم فتح البوت 🔑\nالقائمة الرئيسية", reply_markup=main_keyboard())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state
    query=update.callback_query; await query.answer(); cid=str(query.from_user.id)
    if not is_authed(cid): return
    if query.data=="best":
        await query.edit_message_text("🔍 يفحص 6 أسواق...")
        best,_=get_best()
        if not best:
            await context.bot.send_message(chat_id=int(cid),text="⚪ لا يوجد بيانات حاليا - حاول بعد دقيقة",reply_markup=main_keyboard())
            return
        msg=format_message(best); setup_bear_images(); img=BEAR_BUY_PATH if best["signal"]=="CALL" else BEAR_SELL_PATH
        await context.bot.send_photo(chat_id=int(cid),photo=open(img,"rb"),caption=msg,reply_markup=main_keyboard()) if os.path.exists(img) else await context.bot.send_message(chat_id=int(cid),text=msg,reply_markup=main_keyboard())
    elif query.data=="analyze":
        await query.edit_message_text("🔍 يفحص 6 أسواق...")
        best,rest=get_best(); all_s=([best]+rest) if best else []
        setup_bear_images()
        for r in all_s[:6]:
            msg=format_message(r); img=BEAR_BUY_PATH if r["signal"]=="CALL" else BEAR_SELL_PATH
            try: await context.bot.send_photo(chat_id=int(cid),photo=open(img,"rb"),caption=msg)
            except: await context.bot.send_message(chat_id=int(cid),text=msg)
        await context.bot.send_message(chat_id=int(cid),text="✅ انتهى",reply_markup=main_keyboard())
    elif query.data=="status":
        best,_=get_best(); txt="📊 V16 - كل 5 دق\n\n"
        for i,s in enumerate(SYMBOLS,1): txt+=f"{i}. {NAMES[s]}\n"
        if best: txt+=f"\n⭐ {best['pair']} {best['alignment']} Score {best['score']}"
        await query.edit_message_text(txt,reply_markup=main_keyboard())
    elif query.data in ["pause","resume"]:
        state["paused"][cid]=query.data=="pause"; save_state(state)
        await query.edit_message_text("⏸️ إيقاف" if query.data=="pause" else "▶️ تشغيل AUTO كل 5 دق ✅",reply_markup=main_keyboard())

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    for cid,ok in list(state.get("auth",{}).items()):
        if not ok or state.get("paused",{}).get(cid): continue
        best,_=get_best()
        if not best:
            logging.warning("get_best None - sending test")
            await context.bot.send_message(chat_id=int(cid), text=" AUTO TEST - البوت شغال ✅\nسيتم الإرسال بعد 5 دق")
            continue
        try:
            msg=format_message(best); setup_bear_images(); img=BEAR_BUY_PATH if best["signal"]=="CALL" else BEAR_SELL_PATH
            if os.path.exists(img): await context.bot.send_photo(chat_id=int(cid),photo=open(img,"rb"),caption=f" اشارة كل 5 دق - V16\n\n{msg}")
            else: await context.bot.send_message(chat_id=int(cid),text=f" اشارة كل 5 دق\n\n{msg}")
        except Exception as e: logging.error(f"auto {e}")

flask_app=Flask(__name__)
@flask_app.route("/")
def home(): return "MAD BEAR V23 STABLE"
def run_flask():
    import time; time.sleep(1)
    flask_app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)),use_reloader=False)



def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=30, first=20)
    app.job_queue.run_repeating(clean, interval=3600, first=10)
    logging.info("V28 FULL - 5MIN CYCLE - NO HEADER - WITH ALL BUTTONS")
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__=="__main__":
    main()
