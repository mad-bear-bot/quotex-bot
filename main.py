import os, logging, json, time
from datetime import datetime, timezone
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_PASSWORD = "7154"
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "AUDUSD=X", "GBPJPY=X"]
NAMES = {"EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "EURJPY=X":"EUR/JPY", "AUDUSD=X":"AUD/USD", "GBPJPY=X":"GBP/JPY"}

STATE_FILE = "/tmp/bot_state_v7_livechart.json"
def load_state():
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return {"auth": {}, "sent": {}, "cooldown": {}, "paused": {}}
def save_state(s):
    try:
        with open(STATE_FILE,'w') as f: json.dump(s,f)
    except: pass
state = load_state()
sent_pairs = state.get("sent", {})
cooldown = state.get("cooldown", {})
logging.basicConfig(level=logging.INFO)

def calculate_rsi(prices, period=14):
    try:
        deltas = np.diff(prices)
        gains = deltas.copy(); gains[gains<0]=0
        losses = -deltas.copy(); losses[losses>0]=0; losses = np.abs(losses)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss==0: return 70 if avg_gain>0 else 50
        rs = avg_gain/avg_loss
        return float(100 - (100/(1+rs)))
    except: return 50

def get_h1_trend(symbol):
    try:
        df_h1 = yf.download(symbol, period="5d", interval="1h", progress=False, auto_adjust=True)
        if len(df_h1) < 50: return "neutral", 0, 50, 0
        try: 
            if hasattr(df_h1.columns, 'levels'): df_h1.columns = df_h1.columns.get_level_values(0)
        except: pass
        closes = df_h1['Close'].values.flatten()
        ema50 = np.mean(closes[-50:])
        last = closes[-1]
        rsi_h1 = calculate_rsi(closes)
        if last > ema50 and rsi_h1 > 50: trend, strength = "bullish", 20
        elif last < ema50 and rsi_h1 < 50: trend, strength = "bearish", 20
        else: trend, strength = "neutral", 0
        return trend, strength, rsi_h1, ema50
    except: return "neutral", 0, 50, 0

def is_news_time():
    now = datetime.now(timezone.utc)
    h, m = now.hour, now.minute
    if h==13 and m>=20: return True, "أخبار USD 13:30 UTC"
    if h==14: return True, "وقت أخبار USD"
    if h>=22 or h<=1: return True, "سوق ميت"
    return False, ""

def analyze_v7(symbol):
    try:
        df_m5 = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df_m5) < 60: return None
        try:
            if hasattr(df_m5.columns, 'levels'): df_m5.columns = df_m5.columns.get_level_values(0)
        except: pass
        closes = df_m5['Close'].values.flatten()
        highs = df_m5['High'].values.flatten()
        lows = df_m5['Low'].values.flatten()
        opens = df_m5['Open'].values.flatten()
        last_close = float(closes[-1]); last_open = float(opens[-1])
        last_high = float(highs[-1]); last_low = float(lows[-1])
        rsi_m5 = calculate_rsi(closes)
        prev_high = float(highs[-25:-1].max()); prev_low = float(lows[-25:-1].min())
        body_top = max(last_open, last_close); body_bottom = min(last_open, last_close)
        body_size = abs(last_close-last_open); wick_upper = last_high-body_top; wick_lower = body_bottom-last_low
        bullish_bos_body = body_top > prev_high and body_size > wick_upper*0.5
        bearish_bos_body = body_bottom < prev_low and body_size > wick_lower*0.5
        bullish_bos_wick = last_close > prev_high; bearish_bos_wick = last_close < prev_low
        ob_bullish = len(closes)>6 and closes[-1] > closes[-2] > closes[-3] and lows[-4] < lows[-5]
        ob_bearish = len(closes)>6 and closes[-1] < closes[-2] < closes[-3] and highs[-4] > highs[-5]
        fvg_bull = len(lows)>4 and lows[-1] > highs[-3]; fvg_bear = len(highs)>4 and highs[-1] < lows[-3]
        h1_trend, h1_strength, rsi_h1, ema_h1 = get_h1_trend(symbol)
        score=0; reasons=[]
        if bullish_bos_body: score+=40; reasons.append("BOS بجسم قوي")
        elif bullish_bos_wick: score+=25; reasons.append("BOS ذيل")
        if bearish_bos_body: score+=40; reasons.append("BOS هابط جسم")
        elif bearish_bos_wick: score+=25; reasons.append("BOS هابط ذيل")
        if ob_bullish or ob_bearish: score+=20; reasons.append("Order Block")
        if fvg_bull or fvg_bear: score+=15; reasons.append("FVG")
        signal_dir=None
        if bullish_bos_body or bullish_bos_wick:
            signal_dir="CALL"
            if h1_trend=="bullish": score+=30; reasons.append(f"H1 صاعد ✅")
            elif h1_trend=="bearish": score-=25; reasons.append(f"H1 هابط ❌")
        elif bearish_bos_body or bearish_bos_wick:
            signal_dir="PUT"
            if h1_trend=="bearish": score+=30; reasons.append(f"H1 هابط ✅")
            elif h1_trend=="bullish": score-=25; reasons.append(f"H1 صاعد ❌")
        if signal_dir=="CALL":
            if rsi_m5>75: score-=20; reasons.append(f"RSI {rsi_m5:.0f} متشبع ❌")
            elif rsi_m5<70: score+=10
        elif signal_dir=="PUT":
            if rsi_m5<25: score-=20; reasons.append(f"RSI {rsi_m5:.0f} متشبع ❌")
            elif rsi_m5>30: score+=10
        if score<60: return None
        conf = 92 if score>=90 else 85 if score>=80 else 78 if score>=70 else 70
        clean = NAMES.get(symbol, symbol.replace("=X",""))
        return {"pair":clean,"symbol":symbol,"signal":signal_dir,"conf":conf,"price":last_close,"reason":"+ ".join(reasons[:3]),"full_reasons":reasons,"score":score,"time":datetime.now().strftime("%H:%M"),"df":df_m5.tail(80),"rsi_m5":rsi_m5,"rsi_h1":rsi_h1,"h1_trend":h1_trend,"is_body":bullish_bos_body or bearish_bos_body,"prev_high":prev_high,"prev_low":prev_low}
    except Exception as e:
        logging.error(f"V7 {e}")
        return None

def get_best_v7():
    all_s=[]
    for sym in SYMBOLS:
        r=analyze_v7(sym)
        if r: all_s.append(r)
    if not all_s: return None,[]
    all_s.sort(key=lambda x:(x['score'],x['conf']), reverse=True)
    return all_s[0], all_s[1:]

def create_live_candle_chart(result, is_best=False):
    """شارت شموع حي مثل بوكت اوبشن"""
    try:
        df = result['df']
        closes = df['Close'].values.flatten()
        opens = df['Open'].values.flatten()
        highs = df['High'].values.flatten()
        lows = df['Low'].values.flatten()
        
        fig = plt.figure(figsize=(12,8), facecolor='#121212')
        gs = fig.add_gridspec(3, 1, height_ratios=[3, 0.8, 0.7], hspace=0.15)
        ax1 = fig.add_subplot(gs[0,0], facecolor='#121212')
        ax2 = fig.add_subplot(gs[1,0], facecolor='#121212')
        ax3 = fig.add_subplot(gs[2,0], facecolor='#121212')
        
        # رسم الشموع
        n = len(closes)
        times = np.arange(n)
        width = 0.6
        for i in range(n):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            color = '#00C853' if c>=o else '#D50000'  # أخضر وأحمر مثل بوكت
            # الفتيل
            ax1.plot([i,i], [l,h], color=color, linewidth=1, alpha=0.8)
            # الجسم
            body_bottom = min(o,c); body_top = max(o,c)
            body_height = abs(c-o)
            if body_height < (h-l)*0.05: body_height = (h-l)*0.05
            rect = mpatches.Rectangle((i-width/2, body_bottom), width, max(body_height, 0.00001), facecolor=color, edgecolor=color, alpha=0.9)
            ax1.add_patch(rect)
        
        # خط الدخول + القمة السابقة
        ax1.axhline(y=result['price'], color='#FFD600', linestyle='--', linewidth=1.5, alpha=0.9, label=f"Entry {result['price']:.5f}")
        ax1.axhline(y=result['prev_high'] if result['signal']=='CALL' else result['prev_low'], color='white', linestyle=':', linewidth=1, alpha=0.5, label=f"Prev {'High' if result['signal']=='CALL' else 'Low'}")
        
        # إشارة
        last_idx = n-1
        sig_color = '#00E676' if result['signal']=='CALL' else '#FF1744'
        ax1.scatter([last_idx], [closes[-1]], color=sig_color, s=300, zorder=10, edcolors='white', linewidth=1.5)
        ax1.annotate(f"{result['signal']} {('⬆️' if result['signal']=='CALL' else '⬇️')} {result['conf']}%", xy=(last_idx, closes[-1]), xytext=(10,20), textcoords='offset points', color='white', fontsize=12, fontweight='bold', bbox=dict(boxstyle='round,pad=0.4', fc=sig_color, alpha=0.9), arrowprops=dict(arrowstyle='->', color='white'))
        
        title = f"{'⭐ BEST ' if is_best else ''}{result['pair']} - {result['signal']} - {result['reason']} - Score {result['score']:.0f} - LIVE M5"
        ax1.set_title(title, color='white', fontsize=11, fontweight='bold', pad=12)
        ax1.grid(True, alpha=0.1, color='gray')
        ax1.tick_params(colors='#888888', labelsize=9)
        ax1.legend(loc='upper left', fontsize=8, facecolor='#1E1E1E', edgecolor='#333', labelcolor='white')
        ax1.set_xlim(-1, n)
        
        # RSI
        rsi_vals=[]
        for i in range(n):
            rsi_vals.append(calculate_rsi(closes[:i+1]) if i>=14 else 50)
        ax2.plot(times, rsi_vals, color='#FF9100', linewidth=1.6)
        ax2.axhline(70, color='#FF1744', linestyle='--', alpha=0.6, linewidth=0.8)
        ax2.axhline(30, color='#00C853', linestyle='--', alpha=0.6, linewidth=0.8)
        ax2.fill_between(times, 70, 100, color='#FF1744', alpha=0.08)
        ax2.fill_between(times, 0, 30, color='#00C853', alpha=0.08)
        ax2.set_ylabel('RSI', color='#888', fontsize=9)
        ax2.set_ylim(0,100)
        ax2.tick_params(colors='#888', labelsize=8)
        ax2.grid(True, alpha=0.08)
        # نقطة RSI الحالية
        ax2.scatter([last_idx], [rsi_vals[-1]], color='#FF9100', s=60, zorder=5)
        ax2.text(last_idx, rsi_vals[-1], f" {rsi_vals[-1]:.0f}", color='#FF9100', fontsize=9, va='center')
        
        # معلومات إضافية
        ax3.axis('off')
        info_text = f"H1 Trend: {result['h1_trend'].upper()} | RSI M5: {result['rsi_m5']:.0f} | H1: {result['rsi_h1']:.0f} | Body Break: {'YES ✅' if result['is_body'] else 'Wick'} | Time: {result['time']} UTC | Real Market (No OTC)"
        ax3.text(0.5, 0.5, info_text, ha='center', va='center', color='#AAAAAA', fontsize=9, bbox=dict(boxstyle='round,pad=0.5', facecolor='#1E1E1E', edgecolor='#333'))
        
        plt.tight_layout()
        path = f"/tmp/live_chart_{result['pair'].replace('/','_')}_{'BEST' if is_best else 'N'}.png"
        plt.savefig(path, dpi=200, facecolor='#121212', bbox_inches='tight')
        plt.close()
        return path
    except Exception as e:
        logging.error(f"Live chart {e}")
        plt.close()
        return None

def is_authed(cid): return str(cid) in state.get("auth", {}) and state["auth"][str(cid)]
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ أفضل إشارة LIVE", callback_data="best"), InlineKeyboardButton("📊 كل الإشارات", callback_data="analyze")],
        [InlineKeyboardButton("📈 حالة V7", callback_data="status"), InlineKeyboardButton("📰 الأخبار", callback_data="news")],
        [InlineKeyboardButton("⏸️ إيقاف", callback_data="pause"), InlineKeyboardButton("▶️ تشغيل", callback_data="resume")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    cid=str(update.effective_chat.id)
    if is_authed(cid): await context.bot.send_message(chat_id=cid, text="✅ تم فتح البوت 🔑 V7 LIVE CHART\n\nشارت شموع حية مثل بوكت أوبشن!", reply_markup=main_keyboard())
    else: await context.bot.send_message(chat_id=cid, text="ادخل الرقم السري للبوت 🔐")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state
    text=update.message.text.strip(); cid=str(update.effective_chat.id)
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    if text==BOT_PASSWORD:
        state["auth"][cid]=True; save_state(state)
        await context.bot.send_message(chat_id=cid, text="تم فتح البوت 🔑\n\n🚀 V7 LIVE CHART\n✅ شارت شموع حية مثل بوكت أوبشن\n✅ H1 + M5 + RSI\n✅ BOS بجسم الشمعة\n\nالآن مع صورة الشارت الحية!", reply_markup=main_keyboard())
    elif not is_authed(cid): await context.bot.send_message(chat_id=cid, text="❌ خطأ\n\nادخل الرقم السري للبوت 🔐")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state, sent_pairs, cooldown
    query=update.callback_query; await query.answer(); cid=str(query.from_user.id)
    if not is_authed(cid): await query.edit_message_text("❌ انتهت الجلسة\n\nادخل الرقم السري للبوت 🔐"); return
    now=time.time()
    if query.data in ["best","analyze","status"]:
        if cooldown.get(cid,0)>now: await query.answer(f"⏳ انتظر {int(cooldown[cid]-now)}ث", show_alert=True); return
        cooldown[cid]=now+15; state["cooldown"]=cooldown; save_state(state)
    if query.data=="best":
        is_news, reason=is_news_time()
        if is_news: await query.edit_message_text(f"📰 فلتر الأخبار\n⚠️ {reason}\n\nلا تتداول الآن", reply_markup=main_keyboard()); return
        await query.edit_message_text("🔍 V7 LIVE يحلل...\nيرسم شارت شموع حية مثل بوكت أوبشن ⭐")
        best,rest=get_best_v7()
        if not best: await context.bot.send_message(chat_id=int(cid), text="⚪ V7: لا يوجد إشارات قوية Score>=60\nالسوق في تجميع", reply_markup=main_keyboard()); return
        if sent_pairs.get(best['pair'],0)>now-600: await context.bot.send_message(chat_id=int(cid), text=f"⚪ {best['pair']} أرسلت قبل قليل", reply_markup=main_keyboard()); return
        chart=create_live_candle_chart(best, True)
        arrow="⬆️" if best['signal']=="CALL" else "⬇️"
        msg=f"""⭐ V7 LIVE - أفضل إشارة + شارت حي ⭐
━━━━━━━━━━━━━━━━━━━━━━
💱 الزوج: {best['pair']} (سوق حقيقي LIVE)
📊 الإشارة: {best['signal']} {arrow}
⏱️ المدة: 3 دقائق | M5 + H1

💰 السعر الحي: {best['price']:.5f}
📈 التحليل: {best['reason']}
🎯 الثقة: {best['conf']}% | ⭐ {best['score']:.0f}/100
📊 RSI M5: {best['rsi_m5']:.0f} | H1: {best['rsi_h1']:.0f} ({best['h1_trend']})
🕐 {best['time']} UTC

📸 الشارت الحي بالأسفل - نفس سعر بوكت أوبشن!
📌 افتح {best['pair']} في بوكت وقارن السعر
💡 دخول 1% فقط"""
        if chart and os.path.exists(chart):
            with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid), photo=p, caption=msg, reply_markup=main_keyboard())
        else: await context.bot.send_message(chat_id=int(cid), text=msg, reply_markup=main_keyboard())
        sent_pairs[best['pair']]=now; state["sent"]=sent_pairs; save_state(state)
    elif query.data=="analyze":
        await query.edit_message_text("🔍 V7 LIVE يفحص...")
        best,rest=get_best_v7()
        all_s=([best]+rest) if best else []
        if not all_s: await context.bot.send_message(chat_id=int(cid), text="⚪ لا يوجد قوي", reply_markup=main_keyboard()); return
        for r in all_s[:3]:
            if sent_pairs.get(r['pair'],0)>now-600: continue
            chart=create_live_candle_chart(r, r==best)
            arrow="⬆️" if r['signal']=="CALL" else "⬇️"
            msg=f"{'⭐ BEST ' if r==best else ''}{r['pair']} {r['signal']} {arrow} {r['conf']}% Score {r['score']:.0f}\n{r['reason']} | RSI {r['rsi_m5']:.0f}"
            if chart and os.path.exists(chart):
                with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid), photo=p, caption=msg)
            else: await context.bot.send_message(chat_id=int(cid), text=msg)
    elif query.data=="status":
        is_news, nr=is_news_time(); best,rest=get_best_v7(); bt=f"{best['pair']} {best['signal']} {best['conf']}%" if best else "لا يوجد"
        await query.edit_message_text(f"📊 V7 LIVE CHART\n✅ البوت: شغال\n🔍 الفحص: 60ث\n💹 6 أزواج حية\n🧠 BOS Body+H1+RSI\n⭐ أفضل: {bt}\n📰 {nr if is_news else 'وقت آمن ✅'}\n⏰ {datetime.now().strftime('%H:%M:%S')} UTC", reply_markup=main_keyboard())
    elif query.data=="news":
        is_news, reason=is_news_time()
        await query.edit_message_text(f"📰 فلتر الأخبار\n{'⚠️ '+reason if is_news else '✅ وقت آمن - يمكن التداول'}", reply_markup=main_keyboard())
    elif query.data in ["pause","resume"]:
        state["paused"][cid]=query.data=="pause"; save_state(state)
        await query.edit_message_text("⏸️ إيقاف" if query.data=="pause" else "▶️ تشغيل ✅", reply_markup=main_keyboard())

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global sent_pairs, state
    now=time.time()
    is_news,_=is_news_time()
    if is_news: return
    for cid,ok in list(state.get("auth",{}).items()):
        if not ok or state.get("paused",{}).get(cid): continue
        best,_=get_best_v7()
        if not best or sent_pairs.get(best['pair'],0)>now-600: continue
        try:
            chart=create_live_candle_chart(best, True)
            arrow="⬆️" if best['signal']=="CALL" else "⬇️"
            msg=f"⭐ V7 LIVE تلقائية ⭐\n{best['pair']} {best['signal']} {arrow} {best['conf']}% Score {best['score']:.0f}\n{best['reason']} | RSI {best['rsi_m5']:.0f} | H1 {best['h1_trend']}"
            if chart and os.path.exists(chart):
                with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid), photo=p, caption=msg)
            else: await context.bot.send_message(chat_id=int(cid), text=msg)
            sent_pairs[best['pair']]=now; state["sent"]=sent_pairs; save_state(state)
        except Exception as e: logging.error(e)

flask_app=Flask(__name__)
@flask_app.route('/')
def home(): return "MAD.BEAR V7 LIVE CANDLE CHART"
def run_flask(): flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
def main():
    if not BOT_TOKEN: logging.error("Missing TOKEN"); return
    Thread(target=run_flask, daemon=True).start()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_signals, interval=60, first=20)
    logging.info("V7 LIVE CANDLE")
    app.run_polling()
if __name__=="__main__": main()
