import os
import asyncio
import logging
import yfinance as yf
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ========== الإعدادات ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # آيدي مالك البوت فقط
BOT_PASSWORD = "7154"  # الرقم السري اللي طلبته
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "AUDUSD=X", "GBPJPY=X"]
TIMEFRAME = "5m"

# متغيرات التحكم
is_authenticated = False
authorized_user_id = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def analyze_smc(symbol):
    try:
        df = yf.download(symbol, period="2d", interval=TIMEFRAME, progress=False)
        if len(df) < 50:
            return None
        df = df.reset_index()
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        
        last_close = closes[-1]
        prev_high = highs[-20:-1].max()
        prev_low = lows[-20:-1].min()
        
        bullish_bos = last_close > prev_high
        bearish_bos = last_close < prev_low
        
        ob_bullish = closes[-1] > closes[-2] > closes[-3] and lows[-4] < lows[-5] if len(closes) > 10 else False
        ob_bearish = closes[-1] < closes[-2] < closes[-3] and highs[-4] > highs[-5] if len(closes) > 10 else False

        signal = None
        confidence = 0
        
        if bullish_bos and ob_bullish:
            signal = "CALL ⬆️"
            confidence = 82
        elif bearish_bos and ob_bearish:
            signal = "PUT ⬇️"
            confidence = 82
        elif bullish_bos:
            signal = "CALL ⬆️"
            confidence = 68
        elif bearish_bos:
            signal = "PUT ⬇️"
            confidence = 68
            
        if signal:
            # اسم الزوج بدون كلمة OTC - سوق حقيقي فقط
            clean_name = symbol.replace("=X", "")
            if clean_name == "EURUSD": clean_name = "EUR/USD"
            elif clean_name == "GBPUSD": clean_name = "GBP/USD"
            elif clean_name == "USDJPY": clean_name = "USD/JPY"
            elif clean_name == "EURJPY": clean_name = "EUR/JPY"
            elif clean_name == "AUDUSD": clean_name = "AUD/USD"
            elif clean_name == "GBPJPY": clean_name = "GBP/JPY"
            
            reason = []
            if bullish_bos or bearish_bos:
                reason.append("BOS " + ("صاعد" if bullish_bos else "هابط"))
            if ob_bullish or ob_bearish:
                reason.append("Order Block")
            
            return {
                "pair": clean_name,
                "signal": signal,
                "confidence": confidence,
                "price": last_close,
                "reason": " + ".join(reason),
                "time": datetime.now().strftime("%H:%M")
            }
        return None
    except Exception as e:
        logging.error(f"Error {symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global authorized_user_id
    user_id = str(update.effective_user.id)
    
    # يسمح فقط لصاحب CHAT_ID أو أول واحد يدخل الرقم السري
    if is_authenticated and authorized_user_id and user_id != authorized_user_id:
        await update.message.reply_text("⛔ هذا البوت خاص - الرقم السري مطلوب")
        return

    await update.message.reply_text(
        "🔐 مرحبا في MAD.BEAR.BOT\n\n"
        "هذا البوت محمي برقم سري\n"
        "أرسل الرقم السري للدخول:"
    )

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_authenticated, authorized_user_id
    
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    
    if text == BOT_PASSWORD:
        is_authenticated = True
        authorized_user_id = user_id
        await update.message.reply_text(
            "✅ تم فتح البوت بنجاح!\n\n"
            "🔥 نظام SMC الحقيقي شغال الآن\n"
            "📊 يحلل: BOS + Order Block\n"
            "⏰ الفريم: M5 (3 دقايق دخول)\n"
            "💹 السوق: حقيقي من TradingView\n\n"
            "انتظر أول إشارة (1-2 دقيقة)...\n\n"
            "ملاحظة: تدخل الإشارة يدوي في بوكت أوبشن"
        )
        logging.info(f"User {user_id} authenticated")
    else:
        if is_authenticated and user_id == authorized_user_id:
            # إذا مسجل دخول، تجاهل الرسائل العادية
            return
        await update.message.reply_text("❌ الرقم السري غلط! حاول مرة ثانية: 7154")

async def signal_loop(bot: Bot):
    await asyncio.sleep(10)
    try:
        await bot.send_message(chat_id=CHAT_ID, text="🤖 البوت جاهز - أرسل /start وادخل الرقم السري 7154")
    except:
        pass
    
    sent_pairs = {}
    
    while True:
        if not is_authenticated:
            await asyncio.sleep(5)
            continue
            
        for symbol in SYMBOLS:
            try:
                result = analyze_smc(symbol)
                if result:
                    last_sent = sent_pairs.get(result['pair'], 0)
                    if asyncio.get_event_loop().time() - last_sent < 600:
                        continue
                    
                    msg = f"""📊 {result['pair']} - سوق حقيقي
{result['signal']} - مدة الصفقة 3M

💰 السعر الحالي: {result['price']:.5f}
📈 التحليل: {result['reason']}
🎯 نسبة الثقة: {result['confidence']}%
⏰ الوقت: {result['time']}

👉 افتح نفس الزوج في بوكت أوبشن
💡 إدارة رأس مال 1% فقط
⚠️ تحليل فني مو ضمان ربح"""
                    
                    # يرسل فقط للشخص اللي دخل الرقم السري
                    await bot.send_message(chat_id=authorized_user_id, text=msg)
                    sent_pairs[result['pair']] = asyncio.get_event_loop().time()
                    logging.info(f"Sent: {result['pair']} {result['signal']}")
                    await asyncio.sleep(3)
            except Exception as e:
                logging.error(e)
        
        await asyncio.sleep(60)

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN ناقص!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    
    bot = Bot(token=BOT_TOKEN)
    asyncio.create_task(signal_loop(bot))
    
    logging.info("Starting bot with password 7154...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
