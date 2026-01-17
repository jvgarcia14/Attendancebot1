import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page tracking list (updated with normalized keys)
EXPECTED_PAGES = {
    "brittanyafree": "Brittanya Free",
    "brittanyapaid": "Brittanya Paid",
    "brownin free": "browin paid",
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
    "asiadollfree": "Asia Doll Free"
}

# Clock-in data storage
clock_ins = {}

# Normalize the tag to match expected keys
def normalize_tag(tag: str) -> str:
    return tag.lower().replace("_", "").replace(" ", "")

# Validate clock-in message format
def validate_clock_in_format(text: str) -> tuple[bool, str, str, str]:
    lines = text.strip().split('\n')
    if len(lines) != 4 or lines[0].strip().upper() != "CLOCK IN":
        return False, "", "", ""
    date = lines[1].strip()
    time = lines[2].strip()
    hashtag = lines[3].strip()
    if not hashtag.startswith('#'):
        return False, "", "", ""
    page_key = normalize_tag(hashtag[1:])
    return True, date, time, page_key

# Handle clock-in message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user.first_name
    valid, date, time, page_key = validate_clock_in_format(text)

    if not valid or page_key not in EXPECTED_PAGES:
        await update.message.reply_text(
            "❌ Invalid CLOCK IN format or unknown page.\n\nUse format:\n\n"
            "CLOCK IN\n"
            "<Month Day, Year> PST\n"
            "<Start Time> - <End Time> PST\n"
            "#page_name"
        )
        return

    clock_ins[page_key] = {
        "user": user,
        "date": date,
        "time": time
    }
    await update.message.reply_text(
        f"✅ Clock-in recorded for *{EXPECTED_PAGES[page_key]}* on {date} ({time}) by {user}."
    )

# Format clock-in status message
def generate_clockin_status_output() -> str:
    clocked_in = []
    missing = []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins:
            clocked_in.append(label)
        else:
            missing.append(label)

    status_msg = "📋 CLOCK IN STATUS:\n"
    if clocked_in:
        status_msg += "✅ Clocked in:\n" + "\n".join(clocked_in) + "\n\n"
    if missing:
        status_msg += "⛔ No Clock In:\n" + "\n".join(missing)
    return status_msg.strip()

# Handle /clockins command
async def clockins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    output = generate_clockin_status_output()
    await update.message.reply_text(output)

# Main bot launcher
def main():
    TOKEN = "8536358814:AAHyg5UeZyCNw14T1T8F5cjQVb9znYgVte0"  # Replace this with your actual bot token
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("clockins", clockins_command))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":

    main()
