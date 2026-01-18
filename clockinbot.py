import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- HELPERS ----------------
def normalize_tag(tag: str) -> str:
    return tag.lower().replace("_", "").replace(" ", "")

# ---------------- EXPECTED PAGES ----------------
RAW_PAGES = {
    "brittanyafree": "Brittanya Free",
    "brittanyapaid": "Brittanya Paid",
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
    "oaklypaid": "Oakly Paid",
    "oaklyfree": "Oakly Free",
    "paris": "Paris",
    "asiadollpaid": "Asia Doll Paid",
    "asiadollfree": "Asia Doll Free",
    "mommycarter": "Mommy Carter",
}

EXPECTED_PAGES = {normalize_tag(k): v for k, v in RAW_PAGES.items()}

# ---------------- STORAGE ----------------
clock_ins = {}

# ---------------- VALIDATION ----------------
def validate_clock_in(text: str):
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

# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    user = update.message.from_user.full_name

    valid, date, time, page_key = validate_clock_in(text)

    if not valid:
        return  # silently ignore non clock-in messages

    if page_key not in EXPECTED_PAGES:
        await update.message.reply_text("❌ Unknown page.")
        return

    clock_ins[page_key] = {
        "user": user,
        "date": date,
        "time": time,
    }

    await update.message.reply_text(
        f"✅ Clock-in recorded for *{EXPECTED_PAGES[page_key]}*\n"
        f"{date}\n"
        f"{time}\n"
        f"by {user}",
        parse_mode="Markdown",
    )

# ---------------- STATUS OUTPUT ----------------
def generate_clockin_status_output() -> str:
    clocked_in = []
    missing = []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins:
            clocked_in.append(label)
        else:
            missing.append(label)

    msg = "📋 *CLOCK IN STATUS:*\n\n"

    msg += "✅ *Clocked in:*\n"
    msg += "\n".join(clocked_in) if clocked_in else "None"

    msg += "\n\n🚫 *No Clock In:*\n"
    msg += "\n".join(missing) if missing else "None"

    return msg

# ---------------- COMMAND ----------------
async def clockins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        generate_clockin_status_output(),
        parse_mode="Markdown",
    )

# ---------------- MAIN ----------------
def main():
    TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("clockins", clockins_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Attendance bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
