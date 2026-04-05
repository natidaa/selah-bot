import threading
from flask import Flask

# This creates a tiny fake website to trick Render into staying alive
app = Flask('')
@app.route('/')
def home():
    return "Bot is legacy and running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# --- CONFIG ---
TOKEN = "8583491216:AAHpnkcZZLScsK6b-24DDJND28nhioVWwYI"
URL = "https://wbnjaftbodhpwsykrsod.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibmphZnRib2RocHdzeWtyc29kIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MTM2NzgsImV4cCI6MjA5MDk4OTY3OH0.RtpIadAogc3XFQjaIcK7SXIQO3_VSX_RP7Gu8MI51-k"
supabase: Client = create_client(URL, KEY)

logging.basicConfig(level=logging.INFO)

# --- TRANSLATIONS ---
STRINGS = {
    'en': {
        'start': "🙏 **Welcome to Selah**\n\nChoose an option:\n1. Type anything to post anonymously.\n2. Click 'Comment' to support others.",
        'disclaimer': "⚠️ **Disclaimer:** This is not professional therapy. If in crisis, call local emergency services.",
        'new_post': "📌 **New Post #",
        'view_comments': "💬 View Comments",
        'add_comment': "➕ Add Comment",
        'prompt_comment': "Type your comment/advice for #",
        'comment_added': "✅ Comment added anonymously.",
        'no_comments': "No comments yet.",
        'comments_for': "💬 Comments for #"
    },
    'am': {
        'start': "🙏 **ወደ ሴላ (Selah) እንኳን ደህና መጡ**\n\nከነዚህ አንዱን ይምረጡ:\n1. ማንኛውንም ሀሳብ በምስጢር ለመለጠፍ እዚህ ይፃፉ።\n2. ሌሎችን ለመርዳት 'አስተያየት' (Comment) የሚለውን ይጫኑ።",
        'disclaimer': "⚠️ **ማስገንዘቢያ:** ይህ የባለሙያ ምክር አገልግሎት አይደለም። አስቸኳይ እርዳታ ከፈለጉ ወደ አምቡላንስ ወይም ፖሊስ ይደውሉ።",
        'new_post': "📌 **አዲስ መልዕክት #",
        'view_comments': "💬 አስተያየቶችን ይመልከቱ",
        'add_comment': "➕ አስተያየት ይስጡ",
        'prompt_comment': "ለ # አስተያየትዎን እዚህ ይፃፉ...",
        'comment_added': "✅ አስተያየትዎ በሚስጥር ተልኳል።",
        'no_comments': "እስካሁን ምንም አስተያየት የለም።",
        'comments_for': "💬 የ # አስተያየቶች:"
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("English 🇺🇸", callback_data="setlang_en"),
        InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="setlang_am")
    ]]
    await update.message.reply_text("Please choose your language / እባክዎ ቋንቋ ይምረጡ:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data.startswith("setlang_"):
        lang = data.split("_")[1]
        supabase.table("bot_users").upsert({"user_id": user_id, "lang": lang}).execute()
        await query.edit_message_text(STRINGS[lang]['start'] + "\n\n" + STRINGS[lang]['disclaimer'], parse_mode='Markdown')

    elif "_" in data:
        action, post_id = data.split("_")
        user_data = supabase.table("bot_users").select("lang").eq("user_id", user_id).single().execute().data
        lang = user_data['lang'] if user_data else 'en'

        if action == "list":
            res = supabase.table("comments").select("text").eq("post_id", post_id).execute()
            comments = [item['text'] for item in res.data]
            text = STRINGS[lang]['comments_for'] + post_id + "\n\n" + ("\n---\n".join(comments) if comments else STRINGS[lang]['no_comments'])
            await context.bot.send_message(chat_id=user_id, text=text)

        elif action == "add":
            context.user_data['is_commenting'] = True
            context.user_data['target_post'] = post_id
            await context.bot.send_message(chat_id=user_id, text=STRINGS[lang]['prompt_comment'] + post_id)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_data = supabase.table("bot_users").select("lang").eq("user_id", user_id).single().execute().data
    lang = user_data['lang'] if user_data else 'en'

    if context.user_data.get('is_commenting'):
        post_id = context.user_data.get('target_post')
        supabase.table("comments").insert({"post_id": post_id, "text": update.message.text}).execute()
        context.user_data['is_commenting'] = False
        await update.message.reply_text(STRINGS[lang]['comment_added'])
    else:
        post_id = str(uuid.uuid4())[:6].upper()
        supabase.table("confessions").insert({"id": post_id, "text": update.message.text}).execute()
        
        keyboard = [[
            InlineKeyboardButton(STRINGS['en']['view_comments'], callback_data=f"list_{post_id}"),
            InlineKeyboardButton(STRINGS['en']['add_comment'], callback_data=f"add_{post_id}")
        ], [
            InlineKeyboardButton(STRINGS['am']['view_comments'], callback_data=f"list_{post_id}"),
            InlineKeyboardButton(STRINGS['am']['add_comment'], callback_data=f"add_{post_id}")
        ]]
        
        users = supabase.table("bot_users").select("user_id").execute().data
        for u in users:
            try:
                await context.bot.send_message(chat_id=u['user_id'], text=f"📌 Post #{post_id}\n\n{update.message.text}", reply_markup=InlineKeyboardMarkup(keyboard))
            except: continue

def main():
    # This line starts the fake website so Render doesn't kill the bot
    keep_alive() 
    
    # This starts your Telegram logic
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Selah Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()