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
    "clockinmorning": "morning",
    "clockinmidshift": "midshift",
    "clockingraveyard": "graveyard",
}

# ---------------- PAGES ----------------
RAW_PAGES = {
    "alannafreeoftv": "Alanna Free / OFTV",
    "alannapaid": "Alanna Paid",
    "alannawelcome": "Alanna Welcome",
    "alexis": "Alexis",
    "allyfree": "Ally Free",
    "allypaid": "Ally Paid",
    "aprilb": "April B",
    "ashley": "Ashley",
    "asiadollpaidfree": "Asia Doll Paid / Free",
    "autumnfree": "Autumn Free",
    "autumnpaid": "Autumn Paid",
    "autumnwelcome": "Autumn Welcome",
    "brifreeoftv": "Bri Free / OFTV",
    "bripaid": "Bri Paid",
    "briwelcome": "Bri Welcome",
    "brittanyamain": "Brittanya Main",
    "brittanyapaidfree": "Brittanya Paid / Free",
    "bronwinfree": "Bronwin Free",
    "bronwinoftvmcarteroftv": "Bronwin OFTV & MCarter OFTV",
    "bronwinpaid": "Bronwin Paid",
    "bronwinwelcome": "Bronwin Welcome",
    "carterpaidfree": "Carter Paid / Free",
    "christipaidfree": "Christi Paid and Free",
    "claire": "Claire",
    "cocofree": "Coco Free",
    "cocopaID": "Coco Paid",
    "cyndiecynthiacolby": "Cyndie, Cynthia & Colby",
    "dandfreeoftv": "Dan D Free / OFTV",
    "dandpaid": "Dan D Paid",
    "dandwelcome": "Dan D Welcome",
    "emilyraypaidfree": "Emily Ray Paid / Free",
    "essiepaidfree": "Essie Paid / Free",
    "gracefree": "Grace Free",
    "haileywfree": "Hailey W Free",
    "haileywpaid": "Hailey W Paid",
    "hazeyfree": "Hazey Free",
    "hazeypaid": "Hazey Paid",
    "hazeywelcome": "Hazey Welcome",
    "honeynoppv": "Honey NO PPV",
    "honeyvip": "Honey VIP",
    "isabellaxizziekay": "Isabella x Izzie Kay",
    "islafree": "Isla Free",
    "islaoftv": "Isla OFTV",
    "islapaid": "Isla Paid",
    "islawelcome": "Isla Welcome",
    "kayleexjasmyn": "Kaylee X Jasmyn",
    "kissingcousinsxvalerievip": "Kissing Cousins X Valerie VIP",
    "lexipaid": "Lexi Paid",
    "lilahfree": "Lilah Free",
    "lilahpaid": "Lilah Paid",
    "livv": "Livv",
    "mathildefree": "Mathilde Free",
    "mathildewelcome": "Mathilde Welcome",
    "mathildepaidxisaxalexalana": "Mathilde Paid x Isa A x Alexa Lana",
    "michellefree": "Michelle Free",
    "michellevip": "Michelle VIP",
    "mommycarter": "Mommy Carter",
    "natalialfree": "Natalia L Free",
    "natalialpaid": "Natalia L Paid",
    "natalialnicolefansly": "Natalia L, Nicole Fansly",
    "natalierfree": "Natalie R Free",
    "natalierpaid": "Natalie R Paid",
    "paris": "Paris",
    "popstfree": "Pops T Free",
    "popstpaid": "Pops T Paid",
    "rubirosefree": "Rubi Rose Free",
    "rubirosepaid": "Rubi Rose Paid",
    "salah": "Salah",
    "sarahc": "Sarah C",
    "skypaidfree": "Sky Paid / Free",
}

EXPECTED_PAGES = {normalize_tag(k): v for k, v in RAW_PAGES.items()}

# ---------------- STORAGE ----------------
clock_ins = {
    "morning": {},
    "midshift": {},
    "graveyard": {},
}

# ---------------- PARSER ----------------
def parse_clock_in(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not any(l.upper() == "CLOCK IN" for l in lines):
        return False, "", "", "", ""

    page_key = ""
    shift = ""

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

    text_lower = update.message.text.lower()

    if not any(tag in text_lower for tag in SHIFT_TAGS):
        return

    valid, date, time, page_key, shift = parse_clock_in(update.message.text)
    if not valid or page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name

    if page_key not in clock_ins[shift]:
        clock_ins[shift][page_key] = {
            "users": set(),
            "date": date,
            "time": time,
        }

    clock_ins[shift][page_key]["users"].add(user)

    await update.message.reply_text(
        f"✅ *{EXPECTED_PAGES[page_key]}* clocked in ({shift})\n{date}\n{time}\nby {user}",
        parse_mode="Markdown",
    )

# ---------------- STATUS GENERATOR ----------------
def generate_shift_status(shift: str, with_names=False) -> str:
    clocked = []
    missing = []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins[shift]:
            users = sorted(clock_ins[shift][key]["users"])
            count = len(users)

            block = f"{label} ({count} chatter{'s' if count > 1 else ''})"
            if with_names:
                for u in users:
                    block += f"\n- {u}"

            clocked.append(block)
        else:
            missing.append(label)

    msg = f"📋 *{shift.upper()} SHIFT CLOCK IN STATUS:*\n\n"
    msg += "✅ *Clocked in:*\n"
    msg += "\n\n".join(clocked) if clocked else "None"
    msg += "\n\n🚫 *No Clock In:*\n"
    msg += "\n".join(missing) if missing else "None"

    return msg

# ---------------- COMMANDS ----------------
async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("morning"), parse_mode="Markdown")

async def midshift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift"), parse_mode="Markdown")

async def graveyard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("graveyard"), parse_mode="Markdown")

async def namemorning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("morning", True), parse_mode="Markdown")

async def namemidshift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift", True), parse_mode="Markdown")

async def namegraveyard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("graveyard", True), parse_mode="Markdown")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for shift in clock_ins:
        clock_ins[shift].clear()
    await update.message.reply_text("♻️ *All clock-ins have been reset.*", parse_mode="Markdown")

async def resetmorning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["morning"].clear()
    await update.message.reply_text("♻️ *Morning shift reset.*", parse_mode="Markdown")

async def resetmidshift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["midshift"].clear()
    await update.message.reply_text("♻️ *Midshift reset.*", parse_mode="Markdown")

async def resetgraveyard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["graveyard"].clear()
    await update.message.reply_text("♻️ *Graveyard shift reset.*", parse_mode="Markdown")

# ---------------- MAIN ----------------
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("morning", morning_command))
    app.add_handler(CommandHandler("midshift", midshift_command))
    app.add_handler(CommandHandler("graveyard", graveyard_command))

    app.add_handler(CommandHandler("namemorning", namemorning_command))
    app.add_handler(CommandHandler("namemidshift", namemidshift_command))
    app.add_handler(CommandHandler("namegraveyard", namegraveyard_command))

    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("resetmorning", resetmorning_command))
    app.add_handler(CommandHandler("resetmidshift", resetmidshift_command))
    app.add_handler(CommandHandler("resetgraveyard", resetgraveyard_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Clock-in bot running (3 shifts, names, resets, silent, no history)...")
    app.run_polling()

if __name__ == "__main__":
    main()
