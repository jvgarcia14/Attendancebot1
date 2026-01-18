import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Normalize helper
def normalize_tag(tag: str) -> str:
    return tag.lower().replace("_", "").replace(" ", "")

# Expected pages (AUTO-normalized)
RAW_PAGES = {
    "brittanyafree": "Brittanya Free",
    "brittanyapaid": "Brittanya Paid",
    "autumnpaid": "Autumn Paid",
    "autumnfree": "Autumn Free",
    "browninfree": "Brownin Free",
    "fansly": "Fansly",
    "kissingcousins": "Kissing Cousins",
    "valerievip": "Valerie VIP",
    "carterpaid": "Carter Paid",
    "carterfree": "Carter Free",
    "charlottepfree": "Charlotte P Free",
    "charlotteppaid": "Charlotte P Paid",
    "gracefree": "Grace Free",
    "emilyraypaid": "Emily Ray Paid",
    "emilyrayfree": "Emily Ray Free",
    "lexipaid": "Lexi Paid",
    "mommycarter": "Mommy Carter",
    "oaklypaid": "Oakly Paid",
    "oaklyfree": "Oakly Free",
    "paris": "Paris",
    "asiadollpaid": "Asia Doll Paid",
    "asiadollfree": "Asia Doll Free",
}

EXPECTED_PAGES = {normalize_tag(k): v for k, v in RAW_PAGES.items()}

# Storage
clock_ins = {}

# Validate message
def validate_clock_in_format(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) < 4:
        return False, "", "", ""

    if lines[0].upper() != "CLOCK IN":
        return False, "", "", ""

    date = lines[1]
    time = lines[2]
    hashtag = lines[3]

    if not hashtag.startswith("#"):
        return False, "", "", ""

    page_key = normalize_tag(hashtag[1:])
    return True, date, time, page_key

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user = update.message.from_user.first_name

    valid, date, time, page_key = validate_clock_in_format(text)

    if not valid:
        await update.message.reply_text(
            "❌ Invalid CLOCK IN format.\n\n"
            "Use:\n"
            "CLOCK IN\n"
            "December 5, 2025 PST\n"
            "8:00 AM - 4:00 PM PST\n"
            "#page_name"
        )
        return

    if page_key not in EXPECTED_PAGES:
        await update.message.reply_text(
            f"❌ Unknown page: #{page_key}"
        )
        return

    clock_ins[page_key] = {
        "user": user,
        "date": date,
        "time": time
    }

    await update.message.reply_text(
        f"✅ Clock-in recorded for *{EXPECTED_PAGES[page_key]}*\n"
        f"📅 {date}\n"
        f"⏰ {time}\n"
        f"👤 {user}",
        parse_mode="Markdown"
    )

# Status output
def generate_clockin_status_output():
    clocked = []
    missing = []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins:
            clocked.append(f"✅ {label}")
        else:
            missing.append(f"⛔ {label}")

    return (
        "📋 *CLOCK IN STATUS*\n\n"
        + "\n".join(clocked)
        + "\n\n"
        + "\n".join(missing)
    )

# /clockins command
async def clockins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        generate_clockin_status_output(),
        parse_mode="Markdown"
    )

# Main
def main():
    TOKEN = "8536358814:AAHyg5UeZyCNw14T1T8F5cjQVb9znYgVte0"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("clockins", clockins_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
