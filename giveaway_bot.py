import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
import os

# Logging configurat profesionist
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = "referrals.json"
USERNAMES_FILE = "usernames.json"
BADGES_FILE = "badges.json"

PREMII = {
    25: "🥉 Badge Bronz + voucher 20 RON",
    50: "🥈 Badge Argint + voucher 50 RON",
    100: "🥇 Badge Aur + premiu special"
}

BADGE_THRESHOLDS = {
    25: "🥉 Badge Bronz",
    50: "🥈 Badge Argint",
    100: "🥇 Badge Aur"
}

def load_data(filename):
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Date persistente
referrals = load_data(DATA_FILE)          # {referrer_id: [invited_user_ids]}
usernames = load_data(USERNAMES_FILE)    # {user_id: username_or_nickname}
badges = load_data(BADGES_FILE)           # {user_id: [badge_names]}

async def check_and_award_badges(update: Update, user_id: str, invited_count: int):
    user_badges = set(badges.get(user_id, []))
    new_badges = []

    for threshold, badge_name in BADGE_THRESHOLDS.items():
        if invited_count >= threshold and badge_name not in user_badges:
            user_badges.add(badge_name)
            new_badges.append(badge_name)

    if new_badges:
        badges[user_id] = list(user_badges)
        save_data(BADGES_FILE, badges)
        msg = "🏅 Felicitări! Ai primit următoarele badge-uri noi:\n" + "\n".join(new_badges)
        await update.message.reply_text(msg)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bot_username = context.bot.username

    # Înregistrează username-ul Telegram
    usernames[user_id] = update.effective_user.username or update.effective_user.full_name
    save_data(USERNAMES_FILE, usernames)

    args = context.args
    if args:
        referrer_id = args[0]
        if referrer_id != user_id:
            referrals.setdefault(referrer_id, [])
            if user_id not in referrals[referrer_id]:
                referrals[referrer_id].append(user_id)
                save_data(DATA_FILE, referrals)
                logger.info(f"User {user_id} added as referral for {referrer_id}")

    unique_link = f"https://t.me/{bot_username}?start={user_id}"

    invited_count = len(referrals.get(user_id, []))
    await check_and_award_badges(update, user_id, invited_count)

    await update.message.reply_text(
        f"👋 Salut, {usernames[user_id]}!\n"
        f"Linkul tău unic pentru giveaway:\n{unique_link}\n"
        "Trimite-l prietenilor să te ajute să câștigi premii!"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    invited = referrals.get(user_id, [])
    if invited:
        invited_list = "\n".join(f"- {usernames.get(uid, uid)}" for uid in invited)
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
        name = usernames.get(user_id, user_id)
        message += f"{i}. {name} - {len(invited_list)} invitați\n"
    await update.message.reply_text(message)

async def membri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users = set(referrals.keys())
    for invited_list in referrals.values():
        all_users.update(invited_list)

    if all_users:
        users_list = "\n".join(usernames.get(u, u) for u in sorted(all_users))
        await update.message.reply_text(f"👥 Toți utilizatorii care și-au generat link:\n{users_list}")
    else:
        await update.message.reply_text("🤷‍♂️ Nu există utilizatori în baza de date încă.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comenzi disponibile:\n"
        "/start - Primești link unic și înregistrezi referral\n"
        "/stats - Vezi câți prieteni ai adus\n"
        "/top - Top 5 utilizatori după invitați\n"
        "/membri - Vezi toți utilizatorii care și-au generat link\n"
        "/leaderboard - Top 10 cu detalii\n"
        "/premii - Vezi premiile disponibile\n"
        "/setusername - Setează-ți un nickname pentru leaderboard\n"
        "/profile - Vezi profilul tău\n"
        "/giveaway187 - Vezi badge-urile și progresul tău\n"
        "/help - Această listă de comenzi"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not referrals:
        await update.message.reply_text("🏆 Nu există date despre invitați încă.")
        return
    top_users = sorted(referrals.items(), key=lambda x: len(x[1]), reverse=True)
    message = "🔥 Top 10 utilizatori după invitați:\n"
    for i, (user_id, invited_list) in enumerate(top_users[:10], 1):
        name = usernames.get(user_id, user_id)
        count = len(invited_list)
        # Progres premiu următor
        next_premiu = None
        for threshold in sorted(PREMII.keys()):
            if count < threshold:
                next_premiu = threshold
                break
        if next_premiu:
            progress = f"{count} din {next_premiu} invitați pentru premiul următor"
        else:
            progress = "🎖️ Ai atins toate premiile disponibile!"
        message += f"{i}. {name} - {count} invitați | {progress}\n"
    await update.message.reply_text(message)

async def premii(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🎁 Premiile disponibile:\n"
    for nr_inv, descriere in sorted(PREMII.items()):
        msg += f"- {nr_inv} invitați: {descriere}\n"
    await update.message.reply_text(msg)

async def setusername(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("✍️ Folosește comanda astfel:\n/setusername <nickname>")
        return
    nickname = args[0]
    usernames[user_id] = nickname
    save_data(USERNAMES_FILE, usernames)
    await update.message.reply_text(f"✅ Nickname-ul tău a fost setat la: {nickname}")

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = usernames.get(user_id, update.effective_user.full_name)
    invited = referrals.get(user_id, [])
    unique_link = f"https://t.me/{context.bot.username}?start={user_id}"
    premii_castigate = [descr for nr, descr in PREMII.items() if len(invited) >= nr]
    premii_text = "\n".join(premii_castigate) if premii_castigate else "Niciun premiu câștigat încă."

    await update.message.reply_text(
        f"👤 Profilul tău:\n"
        f"Nume: {name}\n"
        f"Invitați aduși: {len(invited)}\n"
        f"Link unic: {unique_link}\n"
        f"Premii câștigate:\n{premii_text}"
    )

# Placeholder-uri funcții avansate (urmează implementare)
async def invita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("↗️ Funcția /invita urmează să fie implementată.")

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    unique_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"🔗 Link-ul tău unic:\n{unique_link}")

async def dailyreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏰ Funcția /dailyreminder urmează să fie implementată.")

async def faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Funcția /faq urmează să fie implementată.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛠️ Funcția /report urmează să fie implementată.")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💸 Funcția /withdraw urmează să fie implementată.")

async def stats_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = len(set(referrals.keys()).union(*referrals.values()))
    total_invited = sum(len(v) for v in referrals.values())
    await update.message.reply_text(
        f"🌍 Statistici globale:\n"
        f"Număr total utilizatori: {total_users}\n"
        f"Număr total invitați: {total_invited}"
    )

async def share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    unique_link = f"https://t.me/{context.bot.username}?start={user_id}"
    msg = (
        f"📲 Hai să participi la giveaway! Folosește linkul meu unic:\n"
        f"{unique_link}\n"
        "Șanse mari să câștigi premii faine! 🚀"
    )
    await update.message.reply_text(msg)

async def moderare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Funcția de moderare automată este în lucru.")

# Funcția /giveaway187 (gamification cu badge-uri)
async def giveaway187(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    invited_count = len(referrals.get(user_id, []))
    user_badges = badges.get(user_id, [])

    await check_and_award_badges(update, user_id, invited_count)

    next_badge_threshold = None
    for threshold in sorted(BADGE_THRESHOLDS.keys()):
        if invited_count < threshold:
            next_badge_threshold = threshold
            break

    progress_msg = f"Invitați actuali: {invited_count}\n"
    if next_badge_threshold:
        progress_msg += f"Mai ai nevoie de {next_badge_threshold - invited_count} invitați pentru {BADGE_THRESHOLDS[next_badge_threshold]}\n"
    else:
        progress_msg += "Ai atins toate badge-urile disponibile! 🏆\n"

    badges_msg = "Badge-uri câștigate:\n" + ("\n".join(user_badges) if user_badges else "Niciun badge câștigat încă.")

    await update.message.reply_text(progress_msg + "\n" + badges_msg)


def main():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        logger.error("Variabila de mediu BOT_TOKEN nu este setată!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlere comenzi
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("membri", membri))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("premii", premii))
    app.add_handler(CommandHandler("setusername", setusername))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("invita", invita))
    app.add_handler(CommandHandler("link", link))
    app.add_handler(CommandHandler("dailyreminder", dailyreminder))
    app.add_handler(CommandHandler("faq", faq))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("stats_global", stats_global))
    app.add_handler(CommandHandler("share", share))
    app.add_handler(CommandHandler("moderare", moderare))

    # Handler nou pentru gamification sub comanda giveaway187
    app.add_handler(CommandHandler("giveaway187", giveaway187))

    print("Botul pornește...") 
    app.run_polling()

if __name__ == "__main__":
    main()
