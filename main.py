import os, json, logging, threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_PAYMENT_INFO, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# --- Flask Health Check (Render Port Error အတွက်) ---
server = Flask(__name__)

@server.route('/')
def index():
    return "Bot is running!", 200

def run_flask():
    # Render ကပေးတဲ့ PORT ကိုယူမယ်၊ မရှိရင် 10000 သုံးမယ်
    port = int(os.environ.get("PORT", 10000))
    server.run(host='0.0.0.0', port=port)

# --- Supabase Setup ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Bot Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # သင့် Static Site URL ကို ဒီမှာထည့်ပါ
    webapp_url = "https://flash-sale-front.onrender.com" 
    keyboard = [[InlineKeyboardButton("Open Shop 🛒", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        f"မင်္ဂလာပါ {update.effective_user.first_name}\nShop ကိုနှိပ်ပြီး ဝယ်ယူနိုင်ပါပြီ။",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ဈေးနှုန်းပြောင်းရန် Command (Admin သီးသန့်)
# သုံးပုံစံ: /setprice ItemName Price
async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    try:
        # ဥပမာ - /setprice 80_Diamonds 1600
        item_name = context.args[0].replace("_", " ")
        new_price = int(context.args[1])
        
        # Supabase ထဲမှာ prices ဆိုတဲ့ table ရှိရပါမယ်
        supabase.table("prices").upsert({"name": item_name, "amount": new_price}).execute()
        
        await update.message.reply_text(f"✅ {item_name} ရဲ့ ဈေးနှုန်းကို {new_price} Ks သို့ ပြောင်းလဲပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text("❌ အသုံးပြုပုံမှားနေပါသည်။\nဥပမာ - `/setprice 80_Diamonds 1600` (Space အစား _ သုံးပါ)")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.effective_message.web_app_data.data)
    context.user_data['pending_order'] = data
    
    summary = (
        f"📝 **Order Summary**\n\nItem: {data['item']}\nPrice: {data['price']} Ks\nGame ID: {data['game_id']}\n\n"
        f"{ADMIN_PAYMENT_INFO}\n\nငွေလွှဲပြေစာ ပို့ပေးပါ။"
    )
    await update.message.reply_text(summary, parse_mode='Markdown')

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_order' not in context.user_data: return
    
    order = context.user_data['pending_order']
    user = update.effective_user
    
    admin_text = f"🚨 **New Order**\nUser: @{user.username}\nItem: {order['item']}\nID: {order['game_id']}\nPrice: {order['price']} Ks"
    
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, caption=admin_text)
    
    # Save to Sales Table
    supabase.table("sales").insert({
        "customer_id": user.id, "item_name": order['item'], "game_id": order['game_id'], "price": order['price']
    }).execute()

    await update.message.reply_text("✅ ပြေစာရပါပြီ။ ခဏစောင့်ပေးပါ။")
    del context.user_data['pending_order']

def main():
    # Flask ကို Background မှာ Run ရန်
    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setprice", set_price))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    print("Bot is running with Port Support...")
    app.run_polling()

if __name__ == '__main__':
    main()
