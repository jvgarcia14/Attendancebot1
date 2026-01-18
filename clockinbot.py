import logging
import os
from datetime import datetime, timezone
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

# ---------------- BOT START TIME ----------------
BOT_START_TIME = datetime.now(timezone.utc)

# ---------------- HELPERS ----------------
def normalize_tag(tag: str) -> str:
    return (
        tag.lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("/", "")
        .replace("&", "")
        .replace("x", "")
    )

# ---------------- SHIFT TAGS ----------------
SHIFT_TAGS = {
    "clockinprime": "prime",
    "clockinmidshift": "midshift",
    "clockinclosing": "closing",
}

# ---------------- PAGES ----------------
RAW_PAGES = {
    "autumnpaid": "Autumn Paid",
    "mommycarter": "Mommy Carter",
    # keep your full page list here (unchanged)
}

EXPECTED_PAGES = {normalize_tag(k): v for k, v in RAW_PAGES.items()}

# ---------------- STORAGE ----------------
clock_ins = {
    "prime": {},
    "midshift": {},
    "closing": {},
}

# ---------------- INIT PAGE ----------------
def init_page(shift, page_key, date, time):
    if page_key not in clock_ins[shift]:
        clock_ins[shift][page_key] = {
            "users": set(),
            "covers": set(),
            "date": date,
            "time": time,
        }

# ---------------- PARSER ----------------
def parse_clock_in(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not any(l.upper() == "CLOCK IN" for l in lines):
        return False, "", "", "", ""

    page_key, shift = "", ""

    for l in lines:
        if l.startswith("#"):
            tag = normalize_tag(l[1:])
            if tag in SHIFT_TAGS:
                shift = SHIFT_TAGS[tag]
            else:
                page_key = tag

    if not page_key or not shift:
        return False, "", "", "", ""

    date = lines[1] if len(lines) > 1 else ""
    time = lines[2] if len(lines) > 2 else ""
    return True, date, time, page_key, shift

# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.message.date < BOT_START_TIME:
        return

    text = update.message.text.lower()
    if not any(tag in text for tag in SHIFT_TAGS):
        return

    valid, date, time, page_key, shift = parse_clock_in(update.message.text)
    if not valid or page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name
    init_page(shift, page_key, date, time)
    clock_ins[shift][page_key]["users"].add(user)

    await update.message.reply_text(
        f"✅ *{EXPECTED_PAGES[page_key]}* clocked in ({shift})\nby {user}",
        parse_mode="Markdown",
    )

# ---------------- COVER HANDLER ----------------
async def cover_clockin(update: Update, context: ContextTypes.DEFAULT_TYPE, shift: str):
    if update.message.date < BOT_START_TIME:
        return

    if not context.args:
        return  # silent

    page_key = normalize_tag(context.args[0])
    if page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name
    init_page(shift, page_key, "", "")
    clock_ins[shift][page_key]["covers"].add(user)

    await update.message.reply_text(
        f"🟡 *{EXPECTED_PAGES[page_key]}* COVER clock-in ({shift})\nby {user}",
        parse_mode="Markdown",
    )

# ---------------- STATUS GENERATOR ----------------
def generate_shift_status(shift: str, with_names=False) -> str:
    clocked, missing = [], []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins[shift]:
            users = clock_ins[shift][key]["users"]
            covers = clock_ins[shift][key]["covers"]

            parts = []
            if users:
                parts.append(f"{len(users)} chatter{'s' if len(users) > 1 else ''}")
            if covers:
                parts.append(f"{len(covers)} cover{'s' if len(covers) > 1 else ''}")

            header = f"{label} ({', '.join(parts)})" if parts else f"{label} (cover)"
            block = header

            if with_names:
                for u in sorted(users):
                    block += f"\n- {u}"
                for c in sorted(covers):
                    block += f"\n- {c} (cover)"

            clocked.append(block)
        else:
            missing.append(label)

    msg = f"📋 *{shift.upper()} SHIFT CLOCK IN STATUS:*\n\n"
    msg += "✅ *Clocked in:*\n"
    msg += "\n\n".join(clocked) if clocked else "None"
    msg += "\n\n🚫 *No Clock In:*\n"
    msg += "\n".join(missing) if missing else "None"
    return msg

# ---------------- VIEW COMMANDS ----------------
async def prime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("prime"), parse_mode="Markdown")

async def midshift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift"), parse_mode="Markdown")

async def closing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("closing"), parse_mode="Markdown")

async def nameprime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("prime", True), parse_mode="Markdown")

async def namemidshift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift", True), parse_mode="Markdown")

async def nameclosing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("closing", True), parse_mode="Markdown")

# ---------------- RESET ----------------
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for s in clock_ins:
        clock_ins[s].clear()
    await update.message.reply_text("♻️ *All clock-ins reset.*", parse_mode="Markdown")

# ---------------- MAIN ----------------
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    # Views
    app.add_handler(CommandHandler("prime", prime_command))
    app.add_handler(CommandHandler("midshift", midshift_command))
    app.add_handler(CommandHandler("closing", closing_command))
    app.add_handler(CommandHandler("nameprime", nameprime_command))
    app.add_handler(CommandHandler("namemidshift", namemidshift_command))
    app.add_handler(CommandHandler("nameclosing", nameclosing_command))

    # Cover clock-ins
    app.add_handler(CommandHandler("clockinprimecover", lambda u, c: cover_clockin(u, c, "prime")))
    app.add_handler(CommandHandler("clockinmidshiftcover", lambda u, c: cover_clockin(u, c, "midshift")))
    app.add_handler(CommandHandler("clockinclosingcover", lambda u, c: cover_clockin(u, c, "closing")))

    # Reset
    app.add_handler(CommandHandler("reset", reset_command))

    # Normal clock-in
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Clock-in bot running (Prime / Midshift / Closing + Cover)...")
    app.run_polling()

if __name__ == "__main__":
    main()
