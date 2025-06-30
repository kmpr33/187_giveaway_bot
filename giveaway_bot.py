import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
import os

# Configurare logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = "referrals.json"

def load_data():
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

referrals = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bot_username = context.bot.username

    args = context.args
    if args:
        referrer_id = args[0]
        if referrer_id != user_id:
            referrals.setdefault(referrer_id, [])
            if user_id not in referrals[referrer_id]:
                referrals[referrer_id].append(user_id)
                save_data(referrals)
                logger.info(f"User {user_id} added as referral for {referrer_id}")

    unique_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"👋 Salut! Linkul tău unic pentru giveaway:\n{unique_link}\n"
        "Trimite-l prietenilor să te ajute să câștigi premii!"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    invited = referrals.get(user_id, [])
    if invited:
        invited_list = "\n".join(f"- {uid}" for uid in invited)
        await update.message.reply_text(
            f"📊 Ai adus {len(invited)} prieteni:\n{invited_list}"
        )
    else:
        await update.message.reply_text("📊 Nu ai adus încă niciun prieten.")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not referrals:
        await update.message.reply_text("🏆 Nu există date despre invitați încă.")
        return

    top_users = sorted(referrals.items(), key=lambda x: len(x[1]), reverse=True)
    message = "🏆 Top 5 utilizatori după invitați:\n"
    for i, (user_id, invited_list) in enumerate(top_users[:5], 1):
        message += f"{i}. User {user_id} - {len(invited_list)} invitați\n"
    await update.message.reply_text(message)

# Funcția nouă pentru /membri
async def membri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Toți userii care au generat link (keys) + invitații lor (values)
    all_users = set(referrals.keys())
    for invited_list in referrals.values():
        all_users.update(invited_list)

    if all_users:
        users_list = "\n".join(str(u) for u in sorted(all_users))
        await update.message.reply_text(f"👥 Toți utilizatorii care și-au generat link:\n{users_list}")
    else:
        await update.message.reply_text("🤷‍♂️ Nu există utilizatori în baza de date încă.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comenzi disponibile:\n"
        "/start - Pornește botul și primești link unic\n"
        "/stats - Vezi câți prieteni ai adus\n"
        "/top - Top utilizatori după invitați\n"
        "/membri - Vezi toți utilizatorii care și-au generat link\n"
        "/help - Afișează această listă de comenzi"
    )

def main():
    TOKEN = "7566606586:AAH89FbG3dx2vMQfhvDOJkPlJod6sIbItDw"  # Tokenul tău secret
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("membri", membri))  # Adăugat handlerul /membri
    app.add_handler(CommandHandler("help", help_command))

    print("Botul pornește...") 
    app.run_polling()

if __name__ == "__main__":
    main()
