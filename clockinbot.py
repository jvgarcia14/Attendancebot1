import logging
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
    return tag.lower().replace("_", "").replace(" ", "")

# ---------------- EXPECTED PAGES ----------------
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
clock_ins = {}

# ---------------- PARSER ----------------
def parse_clock_in(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not any(l.upper() == "CLOCK IN" for l in lines):
        return False, "", "", ""

    page_key = ""
    for l in lines:
        if l.startswith("#") and l.lower() != "#clockin":
            page_key = normalize_tag(l[1:])
            break

    if not page_key:
        return False, "", "", ""

    date = lines[1] if len(lines) > 1 else ""
    time = lines[2] if len(lines) > 2 else ""

    return True, date, time, page_key

# ---------------- MESSAGE HANDLER ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # ❌ IGNORE HISTORY
    if update.message.date < BOT_START_TIME:
        return

    text_lower = update.message.text.lower()

    # ❌ ONLY react if #clockin exists
    if "#clockin" not in text_lower:
        return

    valid, date, time, page_key = parse_clock_in(update.message.text)

    # ❌ Silent fail on invalid or unknown page
    if not valid or page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name

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
    import os
    TOKEN = os.getenv("BOT_TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("clockins", clockins_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Attendance bot running (no history, silent mode)...")
    app.run_polling()

if __name__ == "__main__":
    main()

