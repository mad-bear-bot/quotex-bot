import os
import threading
import logging
import yfinance as yf
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PASSWORD = "7154"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "AUDUSD=X", "GBPJPY=X"]

is_authenticated = False
authorized_chat_id = None
sent_pairs = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === صفحة وهمية عشان Render ما يعلق ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return f"MAD.BEAR.BOT Running - Auth: {is_authenticated} - Time: {datetime.now()}"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)

# === تحليل SMC ===
def analyze_smc(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df) < 50:
            return None
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        last_close = float(closes[-1])
        prev_high = float(highs[-20:-1].max())
        prev_low = float(lows[-20:-1].min())
        
        bullish_bos = last_close > prev_high
        bearish_bos = last_close < prev_low
        ob_bullish = closes[-1] > closes[-2] > closes[-3] and lows[-4] < lows[-5] if len(closes) > 10 else False
        ob_bearish = closes[-1] < closes[-2] < closes[-3] and highs[-4] > highs[-5] if len(closes) > 10 else False

        signal = None
        conf = 0
        if bullish_bos and ob_bullish:
            signal, conf = "CALL ⬆️", 82
        elif bearish_bos and ob_bearish:
            signal, conf = "PUT ⬇️", 82
        elif bullish_bos:
            signal, conf = "CALL ⬆️", 68
        elif bearish_bos:
            signal, conf = "PUT ⬇️", 68
            
        if signal:
            names = {"EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "EURJPY=X":"EUR/JPY", "AUDUSD=X":"AUD/USD", "GBPJPY=X":"GBP/JPY"}
            clean = names.get(symbol, symbol.replace("=X",""))
            reason = []
            if bullish_bos or bearish_bos:
                reason.append("BOS " + ("صاعد" if bullish_bos else "هابط"))
            if ob_bullish or ob_bearish:
                reason.append("Order Block")
            return {"pair": clean, "signal": signal, "conf": conf, "price": last_close, "reason": " + ".join(reason), "time": datetime.now().strftime("%H:%M")}
        return None
    except Exception as e:
        logging.error(f"Analyze error {symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_authenticated, authorized_chat_id
    if is_authenticated and str(update.effective_chat.id) == str(authorized_chat_id):
        await update.message.reply_text("✅ انت مسجل دخول\nالبوت يفحص السوق كل دقيقة...")
        return
    await update.message.reply_text("🔐 MAD.BEAR.BOT\nأرسل الرقم السري:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_authenticated, authorized_chat_id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    if text == BOT_PASSWORD:
        is_authenticated = True
        authorized_chat_id = chat_id
        await update.message.reply_text(
            "✅ تم فتح البوت بنجاح!\n\n"
            "🔥 نظام SMC شغال الآن\n"
            "📊 BOS + Order Block\n"
            "⏰ M5 - دخول 3M\n"
            "💹 سوق حقيقي\n\n"
            "انتظر أول إشارة..."
        )
        logging.info(f"Authenticated {chat_id}")
        return
    
    if is_authenticated and str(chat_id) == str(authorized_chat_id):
        await update.message.reply_text("👀 البوت شغال... يفحص السوق كل دقيقة")
    else:
        await update.message.reply_text("❌ غلط! أرسل 7154")

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global is_authenticated, authorized_chat_id, sent_pairs
    if not is_authenticated or not authorized_chat_id:
        return
    for symbol in SYMBOLS:
        try:
            result = analyze_smc(symbol)
            if result:
                import time
                last = sent_pairs.get(result['pair'], 0)
                if time.time() - last < 600:
                    continue
                msg = f"""📊 {result['pair']} - سوق حقيقي
{result['signal']} - 3M

💰 {result['price']:.5f}
📈 {result['reason']}
🎯 {result['conf']}%
⏰ {result['time']}

👉 بوكت أوبشن - 1% رأس مال"""
                await context.bot.send_message(chat_id=authorized_chat_id, text=msg)
                sent_pairs[result['pair']] = time.time()
                logging.info(f"Sent {result['pair']} {result['signal']}")
        except Exception as e:
            logging.error(f"Loop error: {e}")

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN missing")
        return
    # شغل موقع وهمي في ثريد ثاني عشان Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=60, first=10)
    logging.info("Bot starting WITH port binding - password 7154")
    app.run_polling()

if __name__ == "__main__":
    main()
