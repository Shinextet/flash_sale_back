import os, json, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TOKEN, ADMIN_ID, ADMIN_PAYMENT_INFO, SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# Supabase Setup
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Render မှာတင်ထားတဲ့ Static Site URL ကို ဒီမှာထည့်ပါ
    webapp_url = "https://flash-sale-front.onrender.com" 
    
    keyboard = [[InlineKeyboardButton("Open Shop 🛒", web_app=WebAppInfo(url=webapp_url))]]
    await update.message.reply_text(
        f"မင်္ဂလာပါ {update.effective_user.first_name}\nShop ကိုနှိပ်ပြီး အော်ဒါတင်နိုင်ပါပြီ။",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mini App ကနေ ပို့လိုက်တဲ့ Data ကို လက်ခံခြင်း
    data = json.loads(update.effective_message.web_app_data.data)
    user_id = update.effective_user.id
    
    summary = (
        f"📝 **Order Summary**\n\n"
        f"Item: {data['item']}\n"
        f"Price: {data['price']} Ks\n"
        f"Game ID: {data['game_id']}\n\n"
        f"{ADMIN_PAYMENT_INFO}\n\n"
        "ငွေလွှဲပြီး Screenshot ပို့ပေးပါ။"
    )
    
    # ယာယီသိမ်းထားခြင်း (Screenshot လာတဲ့အခါ သုံးဖို့)
    context.user_data['pending_order'] = data
    await update.message.reply_text(summary, parse_mode='Markdown')

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'pending_order' not in context.user_data:
        return

    order = context.user_data['pending_order']
    user = update.effective_user
    
    # Admin ထံ အကြောင်းကြားစာ ပို့ခြင်း
    admin_text = (
        f"🚨 **New Order Alert**\n"
        f"Customer: @{user.username} (ID: {user.id})\n"
        f"Item: {order['item']}\n"
        f"Game ID: {order['game_id']}\n"
        f"Price: {order['price']} Ks"
    )
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=admin_text
    )
    
    # Supabase ထဲ သိမ်းခြင်း (Optional)
    supabase.table("sales").insert({
        "customer_id": user.id,
        "item_name": order['item'],
        "game_id": order['game_id'],
        "price": order['price']
    }).execute()

    await update.message.reply_text("ပြေစာရပါပြီ။ Admin မှ စစ်ဆေးပြီး ၁၀ မိနစ်အတွင်း ထည့်ပေးပါမည်။ ✅")
    del context.user_data['pending_order']

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
