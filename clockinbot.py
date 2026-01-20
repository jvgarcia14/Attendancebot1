import logging
import os
import difflib
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
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

# ---------------- TIMEZONE ----------------
PH_TZ = ZoneInfo("Asia/Manila")

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

def to_ph_time(dt: datetime) -> datetime:
    return dt.astimezone(PH_TZ)

def suggest_page(input_key: str):
    matches = difflib.get_close_matches(
        input_key, EXPECTED_PAGES.keys(), n=1, cutoff=0.7
    )
    return matches[0] if matches else None

# ---------------- SHIFTS ----------------
SHIFT_TAGS = {
    "clockinprime": "prime",
    "clockinmidshift": "midshift",
    "clockinclosing": "closing",
}

SHIFT_CUTOFFS = {
    "prime": time(8, 0),
    "midshift": time(16, 0),
    "closing": time(0, 0),
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
    "emilyray": "Emily Ray",
    "essiepaidfree": "Essie Paid / Free",
    "fanslyteam1": "Fansly Team1",
    "fanslyteam2": "Fansly Team2",
    "fanslyteam3": "Fansly Team3",
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
    "mathildepaid": "Mathilde Paid",
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
    "prime": {},
    "midshift": {},
    "closing": {},
}

def init_page(shift, page_key):
    if page_key not in clock_ins[shift]:
        clock_ins[shift][page_key] = {
            "users": {},
            "covers": {},
        }

# ---------------- PARSER ----------------
def parse_clock_in(text: str):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not any(l.upper() == "CLOCK IN" for l in lines):
        return False, "", ""

    page_key, shift = "", ""
    for l in lines:
        if l.startswith("#"):
            tag = normalize_tag(l[1:])
            if tag in SHIFT_TAGS:
                shift = SHIFT_TAGS[tag]
            else:
                page_key = tag

    if not page_key or not shift:
        return False, "", ""
    return True, page_key, shift

# ---------------- CLOCK-IN MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.message.date < BOT_START_TIME:
        return

    text = update.message.text.lower()
    if not any(tag in text for tag in SHIFT_TAGS):
        return

    valid, page_key, shift = parse_clock_in(update.message.text)
    if not valid:
        return

    if page_key not in EXPECTED_PAGES:
        suggestion = suggest_page(page_key)
        if suggestion:
            await update.message.reply_text(
                f"❗ Page not recognized.\nDid you mean: #{suggestion}"
            )
        return

    user = update.message.from_user.full_name
    ph_time = to_ph_time(update.message.date)

    init_page(shift, page_key)
    clock_ins[shift][page_key]["users"][user] = ph_time

    await update.message.reply_text(
        f"✅ *{EXPECTED_PAGES[page_key]}* clocked in ({shift})\n"
        f"{ph_time.strftime('%I:%M %p')} PH\nby {user}",
        parse_mode="Markdown",
    )

# ---------------- COVER CLOCK-IN ----------------
async def cover_clockin(update: Update, context: ContextTypes.DEFAULT_TYPE, shift: str):
    if update.message.date < BOT_START_TIME or not context.args:
        return

    page_key = normalize_tag(context.args[0])
    if page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name
    ph_time = to_ph_time(update.message.date)

    init_page(shift, page_key)
    clock_ins[shift][page_key]["covers"][user] = ph_time

    await update.message.reply_text(
        f"🟡 *{EXPECTED_PAGES[page_key]}* COVER ({shift})\n"
        f"{ph_time.strftime('%I:%M %p')} PH\nby {user}",
        parse_mode="Markdown",
    )

# ---------------- STATUS GENERATORS ----------------
def generate_shift_status(shift: str, with_names=False):
    clocked = []
    missing = []

    for key, label in EXPECTED_PAGES.items():
        if key in clock_ins[shift]:
            users = clock_ins[shift][key]["users"]
            covers = clock_ins[shift][key]["covers"]

            parts = []
            if users:
                parts.append(f"{len(users)} chatter{'s' if len(users) != 1 else ''}")
            if covers:
                parts.append(f"{len(covers)} cover{'s' if len(covers) != 1 else ''}")

            header = f"{label} ({', '.join(parts)})" if parts else f"{label} (cover)"

            block = header
            if with_names:
                for u in users:
                    block += f"\n- {u}"
                for c in covers:
                    block += f"\n- {c} (cover)"

            clocked.append(block)
        else:
            missing.append(label)

    msg = f"📋 *{shift.upper()} SHIFT CLOCK-IN STATUS:*\n\n"

    msg += "✅ *Clocked in:*\n"
    msg += "\n\n".join(clocked) if clocked else "None"

    msg += "\n\n🚫 *No Clock In:*\n"
    msg += "\n".join(missing) if missing else "None"

    return msg

def generate_late_status(shift: str):
    cutoff = SHIFT_CUTOFFS[shift]
    blocks = []

    for key, label in EXPECTED_PAGES.items():
        if key not in clock_ins[shift]:
            continue

        late = []
        for u, t in clock_ins[shift][key]["users"].items():
            if t.time() > cutoff:
                late.append(f"- {u} ({t.strftime('%I:%M %p')})")
        for c, t in clock_ins[shift][key]["covers"].items():
            if t.time() > cutoff:
                late.append(f"- {c} (cover, {t.strftime('%I:%M %p')})")

        if late:
            blocks.append(f"*{label}*\n" + "\n".join(late))

    if not blocks:
        return f"⏰ *{shift.upper()} LATE*\n\nNo late clock-ins 🎉"
    return f"⏰ *{shift.upper()} LATE*\n\n" + "\n\n".join(blocks)

# ---------------- COMMANDS ----------------
async def prime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("prime"), parse_mode="Markdown")

async def midshift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift"), parse_mode="Markdown")

async def closing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("closing"), parse_mode="Markdown")

async def nameprime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("prime", True), parse_mode="Markdown")

async def namemidshift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("midshift", True), parse_mode="Markdown")

async def nameclosing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_shift_status("closing", True), parse_mode="Markdown")

async def primelate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_late_status("prime"), parse_mode="Markdown")

async def midshiftlate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_late_status("midshift"), parse_mode="Markdown")

async def closinglate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(generate_late_status("closing"), parse_mode="Markdown")

async def late(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        generate_late_status("prime") + "\n\n" +
        generate_late_status("midshift") + "\n\n" +
        generate_late_status("closing")
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for s in clock_ins:
        clock_ins[s].clear()
    await update.message.reply_text("♻️ All shifts reset.")

async def resetprime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["prime"].clear()
    await update.message.reply_text("♻️ Prime reset.")

async def resetmidshift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["midshift"].clear()
    await update.message.reply_text("♻️ Midshift reset.")

async def resetclosing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clock_ins["closing"].clear()
    await update.message.reply_text("♻️ Closing reset.")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reset(update, context)

# ---------------- MAIN ----------------
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("prime", prime))
    app.add_handler(CommandHandler("midshift", midshift))
    app.add_handler(CommandHandler("closing", closing))

    app.add_handler(CommandHandler("nameprime", nameprime))
    app.add_handler(CommandHandler("namemidshift", namemidshift))
    app.add_handler(CommandHandler("nameclosing", nameclosing))

    app.add_handler(CommandHandler("primelate", primelate))
    app.add_handler(CommandHandler("midshiftlate", midshiftlate))
    app.add_handler(CommandHandler("closinglate", closinglate))
    app.add_handler(CommandHandler("late", late))

    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("resetprime", resetprime))
    app.add_handler(CommandHandler("resetmidshift", resetmidshift))
    app.add_handler(CommandHandler("resetclosing", resetclosing))
    app.add_handler(CommandHandler("rest", rest))

    app.add_handler(CommandHandler("clockinprimecover", lambda u, c: cover_clockin(u, c, "prime")))
    app.add_handler(CommandHandler("clockinmidshiftcover", lambda u, c: cover_clockin(u, c, "midshift")))
    app.add_handler(CommandHandler("clockinclosingcover", lambda u, c: cover_clockin(u, c, "closing")))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Attendance bot running (FINAL FIXED VERSION)")
    app.run_polling()

if __name__ == "__main__":
    main()



