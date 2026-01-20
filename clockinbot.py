import logging
import os
import difflib
from datetime import datetime, timezone, time, timedelta, date
from zoneinfo import ZoneInfo
from typing import Optional, List, Tuple

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

# ---------------- TIMEZONE ----------------
PH_TZ = ZoneInfo("Asia/Manila")

# ---------------- BOT START TIME ----------------
BOT_START_TIME = datetime.now(timezone.utc)

# ---------------- DAY RESET TIME (PH) ----------------
RESET_TIME_PH = time(6, 0)  # 6:00 AM PH

# ---------------- TABLE PAGINATION ----------------
PAGE_SIZE = 12  # /prime shows page 1 of 12 rows

# ---------------- OPTIONAL DB (POSTGRES) ----------------
DB_ENABLED = False
conn = None
try:
    import psycopg2  # pip install psycopg2-binary
except Exception:
    psycopg2 = None


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


def ph_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(PH_TZ)


def attendance_day_for(ph_dt: datetime) -> date:
    """
    Attendance "day" starts at 6:00 AM PH time.
    If time is before 6AM, it belongs to the previous calendar date.
    """
    if ph_dt.time() < RESET_TIME_PH:
        return ph_dt.date() - timedelta(days=1)
    return ph_dt.date()


def suggest_page(input_key: str):
    matches = difflib.get_close_matches(input_key, EXPECTED_PAGES.keys(), n=1, cutoff=0.7)
    return matches[0] if matches else None


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def split_for_telegram(text: str, max_len: int = 3900) -> List[str]:
    """
    Split long text into Telegram-safe chunks (keeps lines intact).
    """
    if len(text) <= max_len:
        return [text]

    parts = []
    while len(text) > max_len:
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    parts.append(text)
    return parts


async def send_long(update: Update, text: str, parse_mode: str = "Markdown"):
    for part in split_for_telegram(text):
        await update.message.reply_text(part, parse_mode=parse_mode)


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

# ---------------- STORAGE (IN-MEMORY CACHE) ----------------
clock_ins = {
    "prime": {},
    "midshift": {},
    "closing": {},
}

ACTIVE_DAY: date = attendance_day_for(ph_now())


def init_page(shift, page_key):
    if page_key not in clock_ins[shift]:
        clock_ins[shift][page_key] = {"users": {}, "covers": {}}


def clear_all_shifts():
    for s in clock_ins:
        clock_ins[s].clear()


# ---------------- DB SETUP ----------------
def db_init():
    global DB_ENABLED, conn
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not set -> running WITHOUT persistence (data will reset on restart).")
        DB_ENABLED = False
        return

    if psycopg2 is None:
        logger.warning("psycopg2 not installed -> running WITHOUT persistence.")
        DB_ENABLED = False
        return

    conn = psycopg2.connect(db_url, sslmode="require")
    conn.autocommit = True
    DB_ENABLED = True

    with conn.cursor() as cur:
        cur.execute(
            """
        CREATE TABLE IF NOT EXISTS attendance_clockins (
            attendance_day DATE NOT NULL,
            shift TEXT NOT NULL,
            page_key TEXT NOT NULL,
            user_name TEXT NOT NULL,
            is_cover BOOLEAN NOT NULL DEFAULT FALSE,
            ph_ts TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (attendance_day, shift, page_key, user_name, is_cover)
        );
        """
        )


def db_upsert(att_day: date, shift: str, page_key: str, user_name: str, is_cover: bool, ph_ts: datetime):
    if not DB_ENABLED:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
        INSERT INTO attendance_clockins (attendance_day, shift, page_key, user_name, is_cover, ph_ts)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (attendance_day, shift, page_key, user_name, is_cover)
        DO UPDATE SET ph_ts = EXCLUDED.ph_ts;
        """,
            (att_day, shift, page_key, user_name, is_cover, ph_ts),
        )


def db_delete_day(att_day: date, shift: Optional[str] = None):
    if not DB_ENABLED:
        return
    with conn.cursor() as cur:
        if shift:
            cur.execute(
                "DELETE FROM attendance_clockins WHERE attendance_day=%s AND shift=%s;",
                (att_day, shift),
            )
        else:
            cur.execute(
                "DELETE FROM attendance_clockins WHERE attendance_day=%s;",
                (att_day,),
            )


def db_load_day(att_day: date):
    """Load today's clock-ins from DB back into memory so redeploy won't wipe state."""
    if not DB_ENABLED:
        return

    clear_all_shifts()

    with conn.cursor() as cur:
        cur.execute(
            """
        SELECT shift, page_key, user_name, is_cover, ph_ts
        FROM attendance_clockins
        WHERE attendance_day = %s;
        """,
            (att_day,),
        )
        rows = cur.fetchall()

    for shift, page_key, user_name, is_cover, ph_ts in rows:
        if shift not in clock_ins:
            continue
        if page_key not in EXPECTED_PAGES:
            continue

        init_page(shift, page_key)
        ph_dt = ph_ts.astimezone(PH_TZ)
        if is_cover:
            clock_ins[shift][page_key]["covers"][user_name] = ph_dt
        else:
            clock_ins[shift][page_key]["users"][user_name] = ph_dt


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


# ---------------- TABLE BUILDING ----------------
Row = Tuple[str, str, int, int, str]  # (tag, label, users, covers, status)


def build_shift_rows(shift: str, missing_only: bool = False) -> List[Row]:
    rows: List[Row] = []
    for key, label in EXPECTED_PAGES.items():
        users = clock_ins[shift].get(key, {}).get("users", {})
        covers = clock_ins[shift].get(key, {}).get("covers", {})

        u = len(users)
        c = len(covers)
        missing = (u == 0 and c == 0)
        if missing_only and not missing:
            continue

        status = "✅" if not missing else "❌"
        tag = f"#{key}"
        rows.append((tag, label, u, c, status))
    return rows


def render_shift_table(rows: List[Row], title: str, page: int, page_size: int) -> str:
    total = len(rows)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = clamp(page, 1, total_pages)

    start = (page - 1) * page_size
    end = min(start + page_size, total)
    shown = rows[start:end]

    msg = (
        f"📊 *{title}*\n"
        f"_Page {page}/{total_pages} • Rows {start+1}-{end} of {total}_\n\n"
        "```\n"
        "Tag              | Page                     | 👥 | 🟡 | St\n"
        "-----------------+--------------------------+----+----+---\n"
    )

    for tag, label, u, c, s in shown:
        tag_col = tag[:15]
        page_col = label[:24]
        msg += f"{tag_col:<15} | {page_col:<24} | {u:^2} | {c:^2} | {s}\n"

    msg += "```\n"
    return msg


def generate_shift_table_page(shift: str, page: int = 1, page_size: int = PAGE_SIZE, missing_only: bool = False) -> str:
    rows = build_shift_rows(shift, missing_only=missing_only)
    title = f"{shift.upper()} SHIFT — MISSING PAGES" if missing_only else f"{shift.upper()} SHIFT — CLOCK-IN STATUS"
    return render_shift_table(rows, title, page, page_size)


# ---------------- CLOCK-IN MESSAGE ----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_DAY

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
            await update.message.reply_text(f"❗ Page not recognized.\nDid you mean: #{suggestion}")
        return

    user = update.message.from_user.full_name
    ph_time = to_ph_time(update.message.date)

    att_day = attendance_day_for(ph_time)
    if att_day != ACTIVE_DAY:
        ACTIVE_DAY = att_day
        db_load_day(ACTIVE_DAY)

    init_page(shift, page_key)
    clock_ins[shift][page_key]["users"][user] = ph_time

    db_upsert(ACTIVE_DAY, shift, page_key, user, False, ph_time)

    await update.message.reply_text(
        f"✅ *{EXPECTED_PAGES[page_key]}* clocked in ({shift})\n"
        f"{ph_time.strftime('%I:%M %p')} PH\nby {user}",
        parse_mode="Markdown",
    )


# ---------------- COVER CLOCK-IN ----------------
async def cover_clockin(update: Update, context: ContextTypes.DEFAULT_TYPE, shift: str):
    global ACTIVE_DAY

    if not update.message or update.message.date < BOT_START_TIME or not context.args:
        return

    page_key = normalize_tag(context.args[0])
    if page_key not in EXPECTED_PAGES:
        return

    user = update.message.from_user.full_name
    ph_time = to_ph_time(update.message.date)

    att_day = attendance_day_for(ph_time)
    if att_day != ACTIVE_DAY:
        ACTIVE_DAY = att_day
        db_load_day(ACTIVE_DAY)

    init_page(shift, page_key)
    clock_ins[shift][page_key]["covers"][user] = ph_time

    db_upsert(ACTIVE_DAY, shift, page_key, user, True, ph_time)

    await update.message.reply_text(
        f"🟡 *{EXPECTED_PAGES[page_key]}* COVER ({shift})\n"
        f"{ph_time.strftime('%I:%M %p')} PH\nby {user}",
        parse_mode="Markdown",
    )


# ---------------- LATE STATUS ----------------
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
    await send_long(update, generate_shift_table_page("prime", page=1), parse_mode="Markdown")

async def midshift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_long(update, generate_shift_table_page("midshift", page=1), parse_mode="Markdown")

async def closing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_long(update, generate_shift_table_page("closing", page=1), parse_mode="Markdown")


def _get_page_arg(context: ContextTypes.DEFAULT_TYPE) -> int:
    # default page 1
    if not context.args:
        return 1
    try:
        return int(context.args[0])
    except Exception:
        return 1


async def primepage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("prime", page=p), parse_mode="Markdown")

async def midshiftpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("midshift", page=p), parse_mode="Markdown")

async def closingpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("closing", page=p), parse_mode="Markdown")


async def primemissingpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("prime", page=p, missing_only=True), parse_mode="Markdown")

async def midshiftmissingpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("midshift", page=p, missing_only=True), parse_mode="Markdown")

async def closingmissingpage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p = _get_page_arg(context)
    await send_long(update, generate_shift_table_page("closing", page=p, missing_only=True), parse_mode="Markdown")


async def primelate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_long(update, generate_late_status("prime"), parse_mode="Markdown")

async def midshiftlate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_long(update, generate_late_status("midshift"), parse_mode="Markdown")

async def closinglate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_long(update, generate_late_status("closing"), parse_mode="Markdown")

async def late(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        generate_late_status("prime")
        + "\n\n"
        + generate_late_status("midshift")
        + "\n\n"
        + generate_late_status("closing")
    )
    await send_long(update, msg, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_DAY
    clear_all_shifts()
    db_delete_day(ACTIVE_DAY)
    await update.message.reply_text("♻️ All shifts reset.")

async def resetprime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_DAY
    clock_ins["prime"].clear()
    db_delete_day(ACTIVE_DAY, "prime")
    await update.message.reply_text("♻️ Prime reset.")

async def resetmidshift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_DAY
    clock_ins["midshift"].clear()
    db_delete_day(ACTIVE_DAY, "midshift")
    await update.message.reply_text("♻️ Midshift reset.")

async def resetclosing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ACTIVE_DAY
    clock_ins["closing"].clear()
    db_delete_day(ACTIVE_DAY, "closing")
    await update.message.reply_text("♻️ Closing reset.")

async def rest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reset(update, context)


# ---------------- AUTO RESET (SAFE ON ANY PTB) ----------------
_last_reset_day = None

async def auto_reset_guard(context: ContextTypes.DEFAULT_TYPE):
    """
    Runs every minute. When PH time hits 6:00 AM, it resets once.
    This avoids JobQueue timezone argument issues across PTB versions.
    """
    global _last_reset_day, ACTIVE_DAY

    now_ph = ph_now()
    today_att_day = attendance_day_for(now_ph)

    if now_ph.hour == 6 and now_ph.minute == 0:
        if _last_reset_day != today_att_day:
            _last_reset_day = today_att_day
            ACTIVE_DAY = today_att_day
            clear_all_shifts()
            db_load_day(ACTIVE_DAY)
            logger.info(f"Auto reset done. ACTIVE_DAY={ACTIVE_DAY.isoformat()}")


# ---------------- MAIN ----------------
def main():
    global ACTIVE_DAY

    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN not set")

    db_init()

    ACTIVE_DAY = attendance_day_for(ph_now())
    db_load_day(ACTIVE_DAY)

    app = ApplicationBuilder().token(TOKEN).build()

    # preview (page 1)
    app.add_handler(CommandHandler("prime", prime))
    app.add_handler(CommandHandler("midshift", midshift))
    app.add_handler(CommandHandler("closing", closing))

    # pagination commands
    app.add_handler(CommandHandler("primepage", primepage))
    app.add_handler(CommandHandler("midshiftpage", midshiftpage))
    app.add_handler(CommandHandler("closingpage", closingpage))

    # missing-only pagination (with #tag)
    app.add_handler(CommandHandler("primemissingpage", primemissingpage))
    app.add_handler(CommandHandler("midshiftmissingpage", midshiftmissingpage))
    app.add_handler(CommandHandler("closingmissingpage", closingmissingpage))

    # late
    app.add_handler(CommandHandler("primelate", primelate))
    app.add_handler(CommandHandler("midshiftlate", midshiftlate))
    app.add_handler(CommandHandler("closinglate", closinglate))
    app.add_handler(CommandHandler("late", late))

    # reset
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("resetprime", resetprime))
    app.add_handler(CommandHandler("resetmidshift", resetmidshift))
    app.add_handler(CommandHandler("resetclosing", resetclosing))
    app.add_handler(CommandHandler("rest", rest))

    # cover clock-ins
    app.add_handler(CommandHandler("clockinprimecover", lambda u, c: cover_clockin(u, c, "prime")))
    app.add_handler(CommandHandler("clockinmidshiftcover", lambda u, c: cover_clockin(u, c, "midshift")))
    app.add_handler(CommandHandler("clockinclosingcover", lambda u, c: cover_clockin(u, c, "closing")))

    # clock-in messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # run guard every 60 seconds to trigger reset at 6:00 AM PH
    app.job_queue.run_repeating(
        auto_reset_guard,
        interval=60,
        first=5,
        name="auto_reset_guard",
    )

    print("🤖 Attendance bot running (PERSISTENT + TABLE VIEW + #TAGS + PAGINATION + AUTO RESET @ 6AM PH)")
    app.run_polling()


if __name__ == "__main__":
    main()
