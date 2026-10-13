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
BOT_PASSWORD = "7154"  # الرقم السري فقط هنا في الكود - لا يظهر للمستخدم أبداً
SYMBOLS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X", "AUDUSD=X", "GBPJPY=X"]
NAMES = {"EURUSD=X":"EUR/USD", "GBPUSD=X":"GBP/USD", "USDJPY=X":"USD/JPY", "EURJPY=X":"EUR/JPY", "AUDUSD=X":"AUD/USD", "GBPJPY=X":"GBP/JPY"}

STATE_FILE = "/tmp/bot_final_clean.json"
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
        avg_gain = np.mean(gains[-period:]); avg_loss = np.mean(losses[-period:])
        if avg_loss==0: return 70
        rs = avg_gain/avg_loss
        return float(100 - (100/(1+rs)))
    except: return 50

def get_h1_trend(symbol):
    try:
        df = yf.download(symbol, period="5d", interval="1h", progress=False, auto_adjust=True)
        if len(df)<50: return "neutral",0,50,0
        try:
            if hasattr(df.columns,'levels'): df.columns=df.columns.get_level_values(0)
        except: pass
        closes=df['Close'].values.flatten()
        ema=np.mean(closes[-50:]); last=closes[-1]; rsi=calculate_rsi(closes)
        if last>ema and rsi>50: return "bullish",20,rsi,ema
        elif last<ema and rsi<50: return "bearish",20,rsi,ema
        else: return "neutral",0,rsi,ema
    except: return "neutral",0,50,0

def is_news_time():
    now=datetime.now(timezone.utc); h=now.hour; m=now.minute
    if h==13 and m>=20: return True,"أخبار USD 13:30"
    if h==14: return True,"وقت أخبار USD"
    if h>=22 or h<=1: return True,"سوق ميت"
    return False,""

def analyze_v7(symbol):
    try:
        df = yf.download(symbol, period="2d", interval="5m", progress=False, auto_adjust=True)
        if len(df)<60: return None
        try:
            if hasattr(df.columns,'levels'): df.columns=df.columns.get_level_values(0)
        except: pass
        closes=df['Close'].values.flatten(); highs=df['High'].values.flatten(); lows=df['Low'].values.flatten(); opens=df['Open'].values.flatten()
        last_close=float(closes[-1]); last_open=float(opens[-1])
        rsi_m5=calculate_rsi(closes)
        prev_high=float(highs[-25:-1].max()); prev_low=float(lows[-25:-1].min())
        body_top=max(last_open,last_close); body_bottom=min(last_open,last_close); body_size=abs(last_close-last_open)
        bullish_body=body_top>prev_high and body_size>0.0001
        bearish_body=body_bottom<prev_low and body_size>0.0001
        bullish_wick=last_close>prev_high; bearish_wick=last_close<prev_low
        ob_bull=len(closes)>6 and closes[-1]>closes[-2]>closes[-3]; ob_bear=len(closes)>6 and closes[-1]<closes[-2]<closes[-3]
        fvg_bull=len(lows)>4 and lows[-1]>highs[-3]; fvg_bear=len(highs)>4 and highs[-1]<lows[-3]
        h1_trend,_,rsi_h1,_=get_h1_trend(symbol)
        score=0; reasons=[]
        if bullish_body: score+=40; reasons.append("BOS صاعد قوي")
        elif bullish_wick: score+=25; reasons.append("BOS صاعد")
        if bearish_body: score+=40; reasons.append("BOS هابط قوي")
        elif bearish_wick: score+=25; reasons.append("BOS هابط")
        if ob_bull or ob_bear: score+=20; reasons.append("Order Block")
        if fvg_bull or fvg_bear: score+=15; reasons.append("FVG")
        signal=None
        if bullish_body or bullish_wick:
            signal="CALL"
            if h1_trend=="bullish": score+=30; reasons.append("H1 صاعد ✅")
            elif h1_trend=="bearish": score-=25; reasons.append("H1 هابط ❌")
        elif bearish_body or bearish_wick:
            signal="PUT"
            if h1_trend=="bearish": score+=30; reasons.append("H1 هابط ✅")
            elif h1_trend=="bullish": score-=25; reasons.append("H1 صاعد ❌")
        if signal=="CALL" and rsi_m5>75: score-=20
        if signal=="PUT" and rsi_m5<25: score-=20
        if score<60: return None
        conf=92 if score>=90 else 85 if score>=80 else 78
        clean=NAMES.get(symbol,symbol.replace("=X",""))
        return {"pair":clean,"symbol":symbol,"signal":signal,"conf":conf,"price":last_close,"reason":"+ ".join(reasons[:3]),"score":score,"time":datetime.now().strftime("%H:%M"),"df":df.tail(80),"rsi_m5":rsi_m5,"rsi_h1":rsi_h1,"h1_trend":h1_trend,"is_body":bullish_body or bearish_body,"prev_high":prev_high,"prev_low":prev_low}
    except: return None

def get_best():
    all_s=[]
    for sym in SYMBOLS:
        r=analyze_v7(sym)
        if r: all_s.append(r)
    if not all_s: return None,[]
    all_s.sort(key=lambda x:(x['score'],x['conf']), reverse=True)
    return all_s[0], all_s[1:]

def create_chart(result, is_best=False):
    try:
        df=result['df']; closes=df['Close'].values.flatten(); opens=df['Open'].values.flatten(); highs=df['High'].values.flatten(); lows=df['Low'].values.flatten()
        fig=plt.figure(figsize=(12,8), facecolor='#121212')
        gs=fig.add_gridspec(3,1,height_ratios=[3,0.8,0.7], hspace=0.15)
        ax1=fig.add_subplot(gs[0,0], facecolor='#121212'); ax2=fig.add_subplot(gs[1,0], facecolor='#121212'); ax3=fig.add_subplot(gs[2,0], facecolor='#121212')
        n=len(closes)
        for i in range(n):
            o,h,l,c=opens[i],highs[i],lows[i],closes[i]
            color='#00C853' if c>=o else '#D50000'
            ax1.plot([i,i],[l,h],color=color,linewidth=1,alpha=0.8)
            body_bottom=min(o,c); body_height=abs(c-o)
            if body_height< (h-l)*0.05: body_height=(h-l)*0.05
            rect=mpatches.Rectangle((i-0.3,body_bottom),0.6,max(body_height,0.00001),facecolor=color,edgecolor=color,alpha=0.9)
            ax1.add_patch(rect)
        ax1.axhline(y=result['price'],color='#FFD600',linestyle='--',linewidth=1.5,alpha=0.9,label=f"Entry {result['price']:.5f}")
        ax1.scatter([n-1],[closes[-1]],color='#00E676' if result['signal']=='CALL' else '#FF1744',s=300,zorder=10,edcolors='white',linewidth=1.5)
        ax1.set_title(f"{'⭐ BEST ' if is_best else ''}{result['pair']} {result['signal']} {result['conf']}% Score {result['score']:.0f} LIVE",color='white',fontsize=11,fontweight='bold')
        ax1.grid(True,alpha=0.1); ax1.tick_params(colors='#888888'); ax1.legend(loc='upper left',fontsize=8,facecolor='#1E1E1E',edgecolor='#333',labelcolor='white'); ax1.set_xlim(-1,n)
        rsi_vals=[calculate_rsi(closes[:i+1]) if i>=14 else 50 for i in range(n)]
        ax2.plot(range(n),rsi_vals,color='#FF9100',linewidth=1.6); ax2.axhline(70,color='#FF1744',linestyle='--',alpha=0.5); ax2.axhline(30,color='#00C853',linestyle='--',alpha=0.5)
        ax2.set_ylabel('RSI',color='#888',fontsize=9); ax2.set_ylim(0,100); ax2.tick_params(colors='#888'); ax2.grid(True,alpha=0.08)
        ax3.axis('off'); info=f"H1: {result['h1_trend'].upper()} | RSI M5:{result['rsi_m5']:.0f} H1:{result['rsi_h1']:.0f} | {result['time']} UTC | Real Market"
        ax3.text(0.5,0.5,info,ha='center',va='center',color='#AAAAAA',fontsize=9,bbox=dict(boxstyle='round,pad=0.5',facecolor='#1E1E1E',edgecolor='#333'))
        plt.tight_layout()
        path=f"/tmp/live_{result['pair'].replace('/','_')}.png"
        plt.savefig(path,dpi=200,facecolor='#121212',bbox_inches='tight'); plt.close()
        return path
    except Exception as e:
        logging.error(f"chart {e}"); plt.close(); return None

def is_authed(cid): return str(cid) in state.get("auth",{}) and state["auth"][str(cid)]
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ أفضل إشارة LIVE",callback_data="best"), InlineKeyboardButton("📊 كل الإشارات",callback_data="analyze")],
        [InlineKeyboardButton("📈 الحالة",callback_data="status"), InlineKeyboardButton("📰 الأخبار",callback_data="news")],
        [InlineKeyboardButton("⏸️ إيقاف",callback_data="pause"), InlineKeyboardButton("▶️ تشغيل",callback_data="resume")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    cid=str(update.effective_chat.id)
    if is_authed(cid):
        await context.bot.send_message(chat_id=cid, text="مرحباً MAD BEAR BOT 🐻\n\n✅ البوت شغال\nاختر من القائمة:", reply_markup=main_keyboard())
    else:
        # رسالة نظيفة بدون كشف الرقم السري نهائياً
        await context.bot.send_message(chat_id=cid, text="مرحباً MAD BEAR BOT 🐻\n\n🔐 أرسل الرقم السري للدخول:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state
    text=update.message.text.strip(); cid=str(update.effective_chat.id)
    # احذف رسالة المستخدم فوراً عشان الرقم السري ما يبقى ظاهر
    try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    except: pass
    if text==BOT_PASSWORD:
        state["auth"][cid]=True; save_state(state)
        await context.bot.send_message(chat_id=cid, text="تم فتح البوت 🔑\n\n🚀 مرحباً MAD BEAR BOT 🐻\n✅ تم الدخول بنجاح", reply_markup=main_keyboard())
        return
    if not is_authed(cid):
        await context.bot.send_message(chat_id=cid, text="❌ الرقم خطأ\n\n🔐 أرسل الرقم السري للدخول:")

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global state, sent_pairs, cooldown
    query=update.callback_query; await query.answer(); cid=str(query.from_user.id)
    if not is_authed(cid): await query.edit_message_text("🔐 انتهت الجلسة\n\nمرحباً MAD BEAR BOT 🐻\nأرسل الرقم السري للدخول:"); return
    now=time.time()
    if query.data in ["best","analyze","status"]:
        if cooldown.get(cid,0)>now: await query.answer(f"⏳ انتظر {int(cooldown[cid]-now)}ث",show_alert=True); return
        cooldown[cid]=now+15; state["cooldown"]=cooldown; save_state(state)
    if query.data=="best":
        is_news,reason=is_news_time()
        if is_news: await query.edit_message_text(f"📰 {reason}\nلا تتداول الآن",reply_markup=main_keyboard()); return
        await query.edit_message_text("🔍 يبحث عن أفضل إشارة LIVE ⭐")
        best,rest=get_best()
        if not best: await context.bot.send_message(chat_id=int(cid),text="⚪ لا يوجد إشارات قوية حالياً Score>=60",reply_markup=main_keyboard()); return
        if sent_pairs.get(best['pair'],0)>now-600: await context.bot.send_message(chat_id=int(cid),text=f"⚪ {best['pair']} أرسلت قبل قليل",reply_markup=main_keyboard()); return
        chart=create_chart(best,True); arrow="⬆️" if best['signal']=="CALL" else "⬇️"
        msg=f"""⭐ أفضل إشارة LIVE ⭐
━━━━━━━━━━━━━━━
💱 {best['pair']} (سوق حقيقي)
📊 {best['signal']} {arrow} | 3M M5+H1
💰 {best['price']:.5f}
📈 {best['reason']}
🎯 {best['conf']}% | ⭐ {best['score']:.0f}/100
RSI M5 {best['rsi_m5']:.0f} H1 {best['rsi_h1']:.0f} ({best['h1_trend']})
🕐 {best['time']} UTC"""
        if chart and os.path.exists(chart):
            with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid),photo=p,caption=msg,reply_markup=main_keyboard())
        else: await context.bot.send_message(chat_id=int(cid),text=msg,reply_markup=main_keyboard())
        sent_pairs[best['pair']]=now; state["sent"]=sent_pairs; save_state(state)
    elif query.data=="analyze":
        await query.edit_message_text("🔍 يفحص...")
        best,rest=get_best()
        all_s=([best]+rest) if best else []
        if not all_s: await context.bot.send_message(chat_id=int(cid),text="⚪ لا يوجد",reply_markup=main_keyboard()); return
        for r in all_s[:3]:
            if sent_pairs.get(r['pair'],0)>now-600: continue
            chart=create_chart(r,r==best)
            msg=f"{'⭐ BEST ' if r==best else ''}{r['pair']} {r['signal']} {r['conf']}%"
            if chart and os.path.exists(chart):
                with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid),photo=p,caption=msg)
            else: await context.bot.send_message(chat_id=int(cid),text=msg)
    elif query.data=="status":
        is_news,nr=is_news_time(); best,_=get_best(); bt=f"{best['pair']} {best['conf']}%" if best else "لا يوجد"
        await query.edit_message_text(f"📊 V7 LIVE\n⭐ أفضل: {bt}\n📰 {nr if is_news else 'وقت آمن ✅'}\n⏰ {datetime.now().strftime('%H:%M:%S')} UTC",reply_markup=main_keyboard())
    elif query.data=="news":
        is_news,reason=is_news_time(); await query.edit_message_text(f"📰 {reason if is_news else '✅ وقت آمن'}",reply_markup=main_keyboard())
    elif query.data in ["pause","resume"]:
        state["paused"][cid]=query.data=="pause"; save_state(state)
        await query.edit_message_text("⏸️ إيقاف" if query.data=="pause" else "▶️ تشغيل ✅",reply_markup=main_keyboard())

async def check_signals(context: ContextTypes.DEFAULT_TYPE):
    global sent_pairs,state
    now=time.time()
    if is_news_time()[0]: return
    for cid,ok in list(state.get("auth",{}).items()):
        if not ok or state.get("paused",{}).get(cid): continue
        best,_=get_best()
        if not best or sent_pairs.get(best['pair'],0)>now-600: continue
        try:
            chart=create_chart(best,True)
            msg=f"⭐ {best['pair']} {best['signal']} {best['conf']}% Score {best['score']:.0f}\n{best['reason']}"
            if chart and os.path.exists(chart):
                with open(chart,'rb') as p: await context.bot.send_photo(chat_id=int(cid),photo=p,caption=msg)
            else: await context.bot.send_message(chat_id=int(cid),text=msg)
            sent_pairs[best['pair']]=now; state["sent"]=sent_pairs; save_state(state)
        except: pass

flask_app=Flask(__name__)
@flask_app.route('/')
def home(): return "MAD BEAR FINAL CLEAN"
def run_flask(): flask_app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
def main():
    if not BOT_TOKEN: logging.error("Missing TOKEN"); return
    Thread(target=run_flask,daemon=True).start()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_message))
    app.job_queue.run_repeating(check_signals,interval=60,first=20)
    logging.info("FINAL CLEAN - NO PASSWORD SHOWN")
    app.run_polling()
if __name__=="__main__": main()
