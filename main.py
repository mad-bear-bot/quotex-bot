
import os, time, logging, requests
from flask import Flask
import threading

# ====== FIX 1: Flask يفتح فوراً ======
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return 'V26 RUNNING - 5MIN CYCLE'

@flask_app.route('/health')
def health():
    return 'OK'

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# شغل Flask في Thread منفصل فوراً - Render يشوف Port مفتوح
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
time.sleep(2)  # اعط Flask ثانيتين يفتح

# ====== FIX 2: امسح Webhook قبل ===
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8631107180:AAEvTM8sVVHZTerraQsGFW1T44oI1PoQ46YU")
try:
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=10)
    logging.info("Webhook deleted")
    time.sleep(1)
except:
    pass

# ====== باقي الكود ======
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import asyncio

# استيراد دوال التحليل من ملفك القديم
try:
    from main_V22_SINGLE import analyze, format_message, setup_bear_images, BEAR_BUY_PATH, BEAR_SELL_PATH, SYMBOLS, state
except:
    # fallback simple
    SYMBOLS = ["EUR/USD","GBP/USD","USD/JPY","AUD/USD","USD/CAD","EUR/JPY"]
    state = {"auth":{},"paused":{}}
    def analyze(s): return None
    def format_message(r): return f"{r}"
    def setup_bear_images(): pass
    BEAR_BUY_PATH = "buy.jpg"
    BEAR_SELL_PATH = "sell.jpg"

logging.basicConfig(level=logging.INFO)

# ====== 5 MIN CYCLE - بدون كلمة فوق الاشارة ======
last_trade_end = {}

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global last_trade_end
    now = time.time()
    
    for cid, ok in list(state.get("auth", {}).items()):
        if not ok or state.get("paused", {}).get(cid):
            continue
        
        # انتظر 5 دقايق بعد اخر صفقة
        if cid in last_trade_end:
            if now - last_trade_end[cid] < 300:  # 300 ثانية = 5 دقايق
                continue
        
        try:
            all_signals = []
            for s in SYMBOLS:
                try:
                    r = analyze(s)
                    if r:
                        all_signals.append(r)
                except:
                    pass
            
            if not all_signals:
                continue
            
            strong = [r for r in all_signals if r.get("align_num")==3 and r.get("score",0)>=82]
            if not strong:
                continue
            
            strong.sort(key=lambda x: (x["score"], x["conf"]), reverse=True)
            best = strong[0]
            
            msg = format_message(best)
            setup_bear_images()
            img = BEAR_BUY_PATH if best["signal"]=="CALL" else BEAR_SELL_PATH
            
            # بدون اي كلمة فوق - نظيف
            try:
                if os.path.exists(img):
                    await context.bot.send_photo(chat_id=int(cid), photo=open(img,"rb"), caption=f"{msg}")
                else:
                    await context.bot.send_message(chat_id=int(cid), text=f"{msg}")
            except Exception as e:
                logging.error(f"send failed {e}")
                await context.bot.send_message(chat_id=int(cid), text=f"{msg}")
            
            last_trade_end[cid] = now
            logging.info(f"V26 sent {best['pair']} to {cid} - next in 5 min")
            
        except Exception as e:
            logging.error(f"auto error {e}")

# Handlers (نفس حقك)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = str(update.effective_chat.id)
    kb = [[InlineKeyboardButton("✅ تفعيل", callback_data="activate")]]
    await update.message.reply_text("MAD BEAR V26 - 5 دقايق بين كل اشارة", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cid = str(q.from_user.id)
    if q.data == "activate":
        state.setdefault("auth",{})[cid]=True
        state.setdefault("paused",{})[cid]=False
        await q.edit_message_text("✅ تم التفعيل - V26 كل 5 دقايق")
        
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    cid = str(update.effective_chat.id)
    if txt == "7154":
        state.setdefault("auth",{})[cid]=True
        await update.message.reply_text("✅ تم - V26 شغال كل 5 دقايق")
    elif txt == "تشغيل ▶️" or "تشغيل" in txt:
        state.setdefault("paused",{})[cid]=False
        await update.message.reply_text("▶️ شغال - كل 5 دقايق اشارة")

# ====== FIX 3: Main بسيط ما يكرش ======
def main():
    # Application
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.job_queue.run_repeating(check_signals, interval=30, first=20)
    
    logging.info("V26 STARTING POLLING - 5MIN CYCLE - NO HEADER")
    # drop_pending_updates=True عشان ما يصير Conflict
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
