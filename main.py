import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from threading import Thread
from typing import Dict, List, Optional, Tuple

import requests
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8456002611:AAEvhsMJFXFuc0OYZCJhQ9WRKyUvryrfsso"  # <-- token inline (as you asked)

BRAND_NAME = "🔥 <b>VIP SIGNAL GROUP</b> 🔥\n⚡ <b>TK CLUB MARUF VIP SIGNAL</b> ⚡"
OWNER_USERNAME = "@OWNER_MARUF_TOP"  # will be clickable automatically
REG_LINK = "https://tkclub2.com/#/register?invitationCode=42584207677"
CHANNEL_LINK = "https://t.me/Vip_signal_group_11"

TARGETS = {
    "MAIN_GROUP": -1003263928753,
    "VIP": -1002892329434,
    "PUBLIC": -1003034758076,  # updated
}

API_URL = "https://api880.inpay88.net/api/webapi/GetNoaverageEmerdList"
BD_TZ = timezone(timedelta(hours=6))

PASSWORD_SHEET_ID = "1foCsja-2HRi8HHjnMP8CyheaLOwk-ZiJ7a5uqs9khvo"
PASSWORD_SHEET_GID = "0"
PASSWORD_FALLBACK = "2222"

MAX_RECOVERY_STEPS = 8
FETCH_TIMEOUT = 6.0

AUTO_WINDOWS = [
    ("21:00", "21:30"),
    ("23:00", "23:30"),
    ("10:00", "10:30"),
    ("12:00", "12:30"),
    ("15:00", "15:30"),
    ("19:00", "19:30"),
]

# =========================
# STICKERS
# =========================
STICKERS = {
    # prediction (forced)
    "PRED_BIG": "CAACAgUAAxkBAAEQYx5pfc4AATgOO5wT5AABMN-bMJl5k_RQAALhHQACDsygVwoi0Z3WbYKyOAQ",
    "PRED_SMALL": "CAACAgUAAxkBAAEQYx1pfc4AAYYby230GOERm9UbVwrbZrcAAl8ZAAKDVphXk0mOoe8u1Zc4BA",

    # session
    "SESSION_START": "CAACAgUAAxkBAAEQYyFpfc4wbxDAkFww3cpExFCaz1iDbQACoB0AAhxruVZktiP7rGZdATgE",
    "SESSION_CLOSE": "CAACAgUAAxkBAAEQYyJpfc4wO83n6lkaDSMVxxFDzq6erwACaB4AAkbvuFbNxjX-zft8RzgE",

    # win/loss set (kept)
    "WIN_BIG": "CAACAgUAAxkBAAEQTjhpcmXknd41yv99at8qxdgw3ivEkAACyRUAAraKsFSky2Ut1kt-hjgE",
    "WIN_SMALL": "CAACAgUAAxkBAAEQTjlpcmXkF8R0bNj0jb1Xd8NF-kaTSQAC7DQAAhnRsVTS3-Z8tj-kajgE",
    "WIN_ALWAYS": "CAACAgUAAxkBAAEQUTZpdFC4094KaOEdiE3njwhAGVCuBAAC4hoAAt0EqVQXmdKVLGbGmzgE",
    "WIN_ANY": "CAACAgUAAxkBAAEQTydpcz9Kv1L2PJyNlbkcZpcztKKxfQACDRsAAoq1mFcAAYLsJ33TdUA4BA",
    "WIN_EXTRA": "CAACAgUAAxkBAAEQWctpeJdTTmIB7FFU1RgNNxaBs5FtggACDxgAAgTqOVf77zJ4WoeanjgE",
    "LOSS": "CAACAgUAAxkBAAEQTytpcz9VQoHyZ5ClbKSqKCJbpqX6yQACahYAAl1wAAFUL9xOdyh8UL84BA",

    "WIN_POOL": [
        "CAACAgUAAxkBAAEQTzNpcz9ns8rx_5xmxk4HHQOJY2uUQQAC3RoAAuCpcFbMKj0VkxPOdTgE",
        "CAACAgUAAxkBAAEQTzRpcz9ni_I4CjwFZ3iSt4xiXxFgkwACkxgAAnQKcVYHd8IiRqfBXTgE",
        "CAACAgUAAxkBAAEQTx9pcz8GryuxGBMFtzRNRbiCTg9M8wAC5xYAAkN_QFWgd5zOh81JGDgE",
    ],
    "SUPER_WIN": {
        2: "CAACAgUAAxkBAAEQTiBpcmUfm9aQmlIHtPKiG2nE2e6EeAACcRMAAiLWqFSpdxWmKJ1TXzgE",
        3: "CAACAgUAAxkBAAEQTiFpcmUgdgJQ_czeoFyRhNZiZI2lwwAC8BcAAv8UqFSVBQEdUW48HTgE",
        4: "CAACAgUAAxkBAAEQTiJpcmUgSydN-tKxoSVdFuAvCcJ3fQACvSEAApMRqFQoUYBnH5Pc7TgE",
        5: "CAACAgUAAxkBAAEQTiNpcmUgu_dP3wKT2k94EJCiw3u52QACihoAArkfqFSlrldtXbLGGDgE",
        6: "CAACAgUAAxkBAAEQTiRpcmUhQJUjd2ukdtfEtBjwtMH4MAACWRgAAsTFqVTato0SmSN-6jgE",
        7: "CAACAgUAAxkBAAEQTiVpcmUhha9HAAF19fboYayfUrm3tdYAAioXAAIHgKhUD0QmGyF5Aug4BA",
        8: "CAACAgUAAxkBAAEQTixpcmUmevnNEqUbr0qbbVgW4psMNQACMxUAAow-qFSnSz4Ik1ddNzgE",
        9: "CAACAgUAAxkBAAEQTi1pcmUmpSxAHo2pvR-GjCPTmkLr0AACLh0AAhCRqFRH5-2YyZKq1jgE",
        10: "CAACAgUAAxkBAAEQTi5pcmUmjmjp7oXg4InxI1dGYruxDwACqBgAAh19qVT6X_-oEywCkzgE",
    },
}

# =========================
# Flask keepalive
# =========================
app = Flask("")

@app.route("/")
def home():
    return "ALIVE"

def run_http():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_http, daemon=True).start()

# =========================
# Time helpers
# =========================
def now_bd() -> datetime:
    return datetime.now(BD_TZ)

def now_bd_str() -> str:
    return now_bd().strftime("%I:%M:%S %p").lstrip("0")

def _hhmm_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)

AUTO_WINDOWS_MIN = [(_hhmm_to_minutes(a), _hhmm_to_minutes(b)) for a, b in AUTO_WINDOWS]

def is_now_in_any_window(now: datetime, custom_window: Optional[Tuple[int, int]]) -> bool:
    mins = now.hour * 60 + now.minute
    windows = [custom_window] if custom_window else AUTO_WINDOWS_MIN
    for a, b in windows:
        if a <= mins < b:
            return True
    return False

def fmt_12h_from_minutes(mins: int) -> str:
    h = mins // 60
    m = mins % 60
    dt = datetime(2000, 1, 1, h, m, tzinfo=BD_TZ)
    return dt.strftime("%I:%M%p").lstrip("0")

def next_window_start(now: datetime, custom_window: Optional[Tuple[int, int]]) -> str:
    mins_now = now.hour * 60 + now.minute
    if custom_window:
        s = custom_window[0]
        hh = s // 60
        mm = s % 60
        dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if (hh * 60 + mm) <= mins_now:
            dt = dt + timedelta(days=1)
        return dt.strftime("%I:%M %p").lstrip("0")

    starts = sorted([_hhmm_to_minutes(a) for a, _ in AUTO_WINDOWS])
    for s in starts:
        if s > mins_now:
            return fmt_12h_from_minutes(s).replace("AM", " AM").replace("PM", " PM")
    return fmt_12h_from_minutes(starts[0]).replace("AM", " AM").replace("PM", " PM")

def calc_current_1m_period(now: datetime) -> str:
    date_str = now.strftime("%Y%m%d")
    total_slots = (now.hour * 60) + now.minute + 1
    return f"{date_str}01{total_slots:04d}"

# =========================
# PASSWORD
# =========================
def fetch_password_a1() -> str:
    try:
        url = (
            f"https://docs.google.com/spreadsheets/d/{PASSWORD_SHEET_ID}/export"
            f"?format=csv&gid={PASSWORD_SHEET_GID}&range=A1"
        )
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return PASSWORD_FALLBACK
        val = r.text.strip().strip('"').strip()
        return val if val else PASSWORD_FALLBACK
    except Exception:
        return PASSWORD_FALLBACK

async def get_live_password() -> str:
    return await asyncio.to_thread(fetch_password_a1)

# =========================
# FETCH
# =========================
def _fetch_latest_issue_sync() -> Optional[dict]:
    payload = {
        "pageSize": 10,
        "pageNo": 1,
        "typeId": 1,
        "language": 0,
        "random": "4ec1d2c67364426aa056214302636756",
        "signature": "D39F9069695C55720235791E0D10D695",
        "timestamp": int(time.time()),
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Origin": "https://dkwin9.com",
        "Referer": "https://dkwin9.com/",
    }
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=FETCH_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if data and "data" in data and "list" in data["data"] and data["data"]["list"]:
                return data["data"]["list"][0]
    except Exception as e:
        print("API Error:", e)
    return None

async def fetch_latest_issue() -> Optional[dict]:
    return await asyncio.to_thread(_fetch_latest_issue_sync)

# =========================
# PREDICTION ENGINE (ZIGZAG + LOSS RESET)
# =========================
class PredictionEngine:
    def __init__(self):
        self.history: List[str] = []
        self.raw_history: List[dict] = []
        self.last_prediction: Optional[str] = None

    def update_history(self, issue_data: dict):
        try:
            number = int(issue_data["number"])
            result_type = "BIG" if number >= 5 else "SMALL"
        except Exception:
            return

        if (not self.raw_history) or (self.raw_history[0].get("issueNumber") != issue_data.get("issueNumber")):
            self.history.insert(0, result_type)
            self.raw_history.insert(0, issue_data)
            self.history = self.history[:120]
            self.raw_history = self.raw_history[:120]

    def calc_confidence(self, streak_loss):
        base = random.randint(95, 99)
        return max(60, base - (streak_loss * 5))

    def get_pattern_signal(self, current_streak_loss):
        # ইতিহাস খুব ছোট হলে র‍্যান্ডম
        if len(self.history) < 4:
            return self.history[0] if self.history else random.choice(["BIG", "SMALL"])

        last = self.history[0]
        prev1 = self.history[1]
        prev2 = self.history[2]

        # =========================================================
        # 🛡️ RULE 1: LOSS RESET (Loss = Copy Paste)
        # =========================================================
        # যদি ১টাও লস হয়, তার মানে আমাদের প্যাটার্ন ভুল হয়েছে।
        # তখন আমরা আর জিগজ্যাগ খুঁজব না। সোজা Last Result Copy (Trend) করব।
        if current_streak_loss > 0:
            return last

        # =========================================================
        # ⚡ RULE 2: ZIGZAG DETECTION (Winning Mode)
        # =========================================================
        # যদি টানা ৩টা রেজাল্ট জিগজ্যাগ হয় (যেমন: B S B বা S B S)
        # এবং আমাদের কোনো লস না থাকে...
        is_zigzag = (last != prev1 and prev1 != prev2)
        
        if is_zigzag:
            # আমরা জিগজ্যাগ কন্টিনিউ করব (উল্টা ধরব)
            return "SMALL" if last == "BIG" else "BIG"

        # =========================================================
        # 🐢 RULE 3: DEFAULT (COPY PASTE)
        # =========================================================
        # যদি জিগজ্যাগ না থাকে এবং লস না হয়, তবে বাই ডিফল্ট Trend Follow (Copy Paste)
        return last

# =========================
# Clickable footer
# =========================
def owner_link() -> str:
    u = OWNER_USERNAME.strip()
    if u.startswith("@"):
        u = u[1:]
    return f"https://t.me/{u}"

def footer_links_html() -> str:
    # clickable single line
    return (
        f"🔗 <b><a href='{REG_LINK}'>Open Account</a></b>  |  "
        f"📣 <b><a href='{CHANNEL_LINK}'>VIP Channel</a></b>  |  "
        f"👤 <b><a href='{owner_link()}'>Owner</a></b>"
    )

# =========================
# Timer (checking spinner)
# =========================
CLOCK_FRAMES = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]

async def run_checking_timer(bot, chat_id: int, msg_id: int, issue: str):
    i = 0
    while state.running and state.active and (state.active.predicted_issue == issue):
        clock = CLOCK_FRAMES[i % len(CLOCK_FRAMES)]
        i += 1
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=(
                    f"{clock} <b>RESULT CHECKING...</b>\n"
                    f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
                    f"🕒 <b>{now_bd_str()}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{footer_links_html()}"
                ),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            break
        await asyncio.sleep(2.0)

# =========================
# STATE
# =========================
@dataclass
class ActiveBet:
    predicted_issue: str
    pick: str
    checking_msg_id: Optional[int] = None
    timer_task: Optional[asyncio.Task] = None
    resolved: bool = False

@dataclass
class BotState:
    unlocked: bool = False
    expected_password: str = PASSWORD_FALLBACK

    # single menu message in admin chat
    admin_chat_id: Optional[int] = None
    panel_message_id: Optional[int] = None
    menu_mode: str = "CHOOSE_CHANNEL"  # CHOOSE_CHANNEL | CHANNEL_PANEL
    waiting_for: Optional[str] = None  # TIME | WINS | SENDMSG

    # which channel to control
    active_target: int = TARGETS["MAIN_GROUP"]

    # session
    running: bool = False
    session_id: int = 0
    engine: PredictionEngine = field(default_factory=PredictionEngine)
    active: Optional[ActiveBet] = None
    last_signal_issue: Optional[str] = None

    # strict lock
    last_resolved_issue: Optional[str] = None

    # schedule / win target
    auto_schedule_enabled: bool = True
    custom_window: Optional[Tuple[int, int]] = None
    stop_after_wins: int = 40
    started_by_schedule: bool = False
    graceful_stop_requested: bool = False

    # stats
    wins: int = 0
    losses: int = 0
    streak_win: int = 0
    streak_loss: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

    stop_event: asyncio.Event = field(default_factory=asyncio.Event)

    # queued message (send after session end)
    queued_messages: List[str] = field(default_factory=list)

state = BotState()

def reset_stats():
    state.wins = 0
    state.losses = 0
    state.streak_win = 0
    state.streak_loss = 0
    state.max_win_streak = 0
    state.max_loss_streak = 0

# =========================
# UI
# =========================
def channel_selector_text() -> str:
    return (
        "📌 <b>CHOOSE CHANNEL</b>\n"
        "যেই গ্রুপ/চ্যানেলে চালাতে চাও সেটায় ক্লিক করো ✅\n\n"
        "⚠️ এরপর সব কন্ট্রোল শুধু ওই চ্যানেলের জন্য কাজ করবে।"
    )

def channel_selector_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ MAIN GROUP", callback_data=f"CHSEL:{TARGETS['MAIN_GROUP']}")],
        [InlineKeyboardButton("✅ VIP", callback_data=f"CHSEL:{TARGETS['VIP']}"),
         InlineKeyboardButton("✅ PUBLIC", callback_data=f"CHSEL:{TARGETS['PUBLIC']}")],
    ])

def channel_name(chat_id: int) -> str:
    for k, v in TARGETS.items():
        if v == chat_id:
            return k.replace("_", " ")
    return str(chat_id)

def panel_text() -> str:
    running = "🟢 RUNNING" if state.running else "🔴 STOPPED"
    custom = (
        f"{fmt_12h_from_minutes(state.custom_window[0])}-{fmt_12h_from_minutes(state.custom_window[1])}"
        if state.custom_window else "Not Set"
    )
    hint = ""
    if state.waiting_for == "TIME":
        hint = "\n\n🕒 এখন টাইম লিখো এভাবে:\n<b>10:00PM-10:30PM</b>"
    elif state.waiting_for == "WINS":
        hint = "\n\n🏆 এখন সংখ্যা লিখো (উদাহরণ: <b>40</b>)"
    elif state.waiting_for == "SENDMSG":
        hint = "\n\n📨 এখন মেসেজ লিখো (সেশন চললে END এর পরে যাবে)"

    return (
        f"🎛 <b>{channel_name(state.active_target)} CONTROL PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: <b>{running}</b>\n"
        f"⏰ Auto: <b>{'ON' if state.auto_schedule_enabled else 'OFF'}</b>\n"
        f"🕒 Select Time: <b>{custom}</b>\n"
        f"🏆 Select Win: <b>{state.stop_after_wins}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 W: <b>{state.wins}</b> | L: <b>{state.losses}</b>\n"
        f"🔥 Streak: W <b>{state.streak_win}</b> | L <b>{state.streak_loss}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {OWNER_USERNAME}"
        f"{hint}"
    )

def panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕒 Select Time", callback_data="SET_TIME"),
         InlineKeyboardButton("🏆 Select Win", callback_data="SET_WINS")],
        [InlineKeyboardButton("📨 Send Message", callback_data="SENDMSG")],
        [InlineKeyboardButton("⏰ Auto: ON" if state.auto_schedule_enabled else "⏰ Auto: OFF", callback_data="TOGGLE_AUTO")],
        [InlineKeyboardButton("⚡ Start 1 MIN", callback_data="START:1M")],
        [InlineKeyboardButton("🧠 Stop After Win", callback_data="STOP:GRACEFUL"),
         InlineKeyboardButton("🛑 Stop Now", callback_data="STOP:FORCE")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="REFRESH_PANEL")],
        [InlineKeyboardButton("⬅️ Back", callback_data="BACK_CHANNELS")],
    ])

# =========================
# Signal / Result texts (Clickable links inside)
# =========================
def signal_text(issue: str, pick: str, conf: int) -> str:
    return (
        f"{BRAND_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎯 <b>ENTRY:</b> <b>{pick}</b>\n"
        f"✨ <b>CONFIDENCE:</b> <b>{conf}%</b>\n"
        f"🧠 <b>RECOVERY:</b> <b>{state.streak_loss}/{MAX_RECOVERY_STEPS}</b>\n"
        f"🕒 <b>TIME:</b> <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{footer_links_html()}"
    )

def result_text(issue: str, res_num: str, res_type: str, pick: str, is_win: bool) -> str:
    head = "✅ <b>WIN CONFIRMED</b>" if is_win else "❌ <b>LOSS CONFIRMED</b>"
    return (
        f"{head}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎰 <b>RESULT:</b> <b>{res_num} ({res_type})</b>\n"
        f"🎯 <b>YOUR PICK:</b> <b>{pick}</b>\n"
        f"📊 <b>W:</b> <b>{state.wins}</b> | <b>L:</b> <b>{state.losses}</b>\n"
        f"🕒 <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{footer_links_html()}"
    )

def summary_text() -> str:
    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0
    nxt = next_window_start(now_bd(), state.custom_window)
    return (
        "🛑 <b>SESSION SUMMARY</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>TOTAL:</b> <b>{total}</b>\n"
        f"✅ <b>WIN:</b> <b>{state.wins}</b>\n"
        f"❌ <b>LOSS:</b> <b>{state.losses}</b>\n"
        f"🎯 <b>WIN RATE:</b> <b>{wr:.1f}%</b>\n"
        f"🔥 <b>MAX WIN STREAK:</b> <b>{state.max_win_streak}</b>\n"
        f"🧊 <b>MAX LOSS STREAK:</b> <b>{state.max_loss_streak}</b>\n"
        f"🕒 <b>CLOSED:</b> <b>{now_bd_str()}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>NEXT SIGNAL:</b> <b>{nxt}</b> 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{footer_links_html()}"
    )

def after_close_review_message() -> str:
    nxt = next_window_start(now_bd(), state.custom_window)
    return (
        "⏺সিগন্যাল কেমন হলো? অবশ্যই এখানে রিভিউ দিবেন 💋\n\n"
        f"<b>{OWNER_USERNAME}</b> ❤️\n\n"
        f"এবং পরবর্তী সিগন্যাল হবে <b>{nxt}</b> ⏰🔥\n\n"
        f"🔗 <a href='{REG_LINK}'>এখানে ক্লিক করে অ্যাকাউন্ট খুলুন</a>\n\n"
        "অ্যাকাউন্ট খুলে ইনবক্সে ইউআইডি দিন। এবং মিনিমাম 300 টাকা ডিপোজিট করে "
        "বট সিগন্যাল উপভোগ করুন এবং আনলিমিটেড হ্যাক নিন 🌟✅\n\n"
        f"<b>{OWNER_USERNAME}</b> ❤️"
    )

# =========================
# PANEL RENDER (single message, no double)
# =========================
async def render_panel(bot):
    if not state.admin_chat_id:
        return
    try:
        if state.menu_mode == "CHOOSE_CHANNEL":
            text = channel_selector_text()
            markup = channel_selector_markup()
        else:
            text = panel_text()
            markup = panel_markup()

        if state.panel_message_id:
            await bot.edit_message_text(
                chat_id=state.admin_chat_id,
                message_id=state.panel_message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        else:
            m = await bot.send_message(
                state.admin_chat_id,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            state.panel_message_id = m.message_id
    except Exception:
        # if edit fails (old/deleted) -> recreate single message and overwrite id
        try:
            m = await bot.send_message(
                state.admin_chat_id,
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            state.panel_message_id = m.message_id
        except Exception:
            pass

# =========================
# send helpers (target only)
# =========================
async def safe_delete(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

async def send_to_target(bot, text: str):
    try:
        await bot.send_message(
            state.active_target,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception:
        pass

async def send_plain_to_target(bot, text: str):
    try:
        await bot.send_message(state.active_target, text, disable_web_page_preview=True)
    except Exception:
        pass

async def send_sticker_target(bot, sticker_id: str):
    try:
        await bot.send_sticker(state.active_target, sticker_id)
    except Exception:
        pass

# =========================
# session control
# =========================
async def flush_queued_messages(bot):
    if not state.queued_messages:
        return
    msgs = state.queued_messages[:]
    state.queued_messages.clear()
    for m in msgs:
        await send_plain_to_target(bot, m)
        await asyncio.sleep(0.7)

async def start_session(bot, started_by_schedule: bool):
    state.session_id += 1
    state.running = True
    state.stop_event.clear()
    state.engine = PredictionEngine()
    state.active = None
    state.last_signal_issue = None
    state.last_resolved_issue = None
    state.started_by_schedule = started_by_schedule
    state.graceful_stop_requested = False
    reset_stats()

    # session start sticker
    await send_sticker_target(bot, STICKERS["SESSION_START"])

async def stop_session(bot, reason: str = "manual"):
    state.session_id += 1
    state.running = False
    state.stop_event.set()

    # stop timer + delete checking message if exists
    if state.active:
        if state.active.timer_task:
            try:
                state.active.timer_task.cancel()
            except Exception:
                pass
        if state.active.checking_msg_id:
            await safe_delete(bot, state.active_target, state.active.checking_msg_id)

    # summary + close sticker
    await send_to_target(bot, summary_text())
    await send_sticker_target(bot, STICKERS["SESSION_CLOSE"])

    # queued message after end
    await flush_queued_messages(bot)

    # review + next signal msg (after close)
    await send_to_target(bot, after_close_review_message())

    state.active = None
    state.started_by_schedule = False
    state.graceful_stop_requested = False

# =========================
# engine loop (STRICT FLOW)
# =========================
async def engine_loop(app: Application, my_session: int):
    bot = app.bot

    while state.running and state.session_id == my_session:
        if state.stop_event.is_set():
            break

        now = now_bd()
        sec = now.second
        current_period = calc_current_1m_period(now)

        # strict: if we already resolved this same period, don't send again
        if state.last_resolved_issue == current_period:
            await asyncio.sleep(0.6)
            continue

        is_safe_time = (5 <= sec <= 40)
        resolved_this_tick = False

        # 1) RESULT PROCESS FIRST
        latest_data = await fetch_latest_issue()
        if latest_data:
            state.engine.update_history(latest_data)

            latest_issue = str(latest_data.get("issueNumber"))
            latest_num = str(latest_data.get("number"))
            latest_type = "BIG" if int(latest_data.get("number")) >= 5 else "SMALL"

            if state.active and state.active.predicted_issue == latest_issue and (not state.active.resolved):
                pick = state.active.pick
                is_win = (pick == latest_type)

                # stop timer (do NOT delete checking yet)
                if state.active.timer_task:
                    try:
                        state.active.timer_task.cancel()
                    except Exception:
                        pass

                # update stats
                if is_win:
                    state.wins += 1
                    state.streak_win += 1
                    state.streak_loss = 0
                    state.max_win_streak = max(state.max_win_streak, state.streak_win)
                else:
                    state.losses += 1
                    state.streak_loss += 1
                    state.streak_win = 0
                    state.max_loss_streak = max(state.max_loss_streak, state.streak_loss)

                # 4) feedback sticker
                if is_win:
                    await send_sticker_target(bot, STICKERS["WIN_ALWAYS"])
                    if state.streak_win in STICKERS["SUPER_WIN"]:
                        await send_sticker_target(bot, STICKERS["SUPER_WIN"][state.streak_win])
                    else:
                        await send_sticker_target(bot, random.choice(STICKERS["WIN_POOL"]))
                    await send_sticker_target(bot, STICKERS["WIN_BIG"] if latest_type == "BIG" else STICKERS["WIN_SMALL"])
                    await send_sticker_target(bot, STICKERS["WIN_ANY"])
                    await send_sticker_target(bot, STICKERS["WIN_EXTRA"])
                else:
                    await send_sticker_target(bot, STICKERS["LOSS"])

                # 5) feedback message
                await send_to_target(bot, result_text(latest_issue, latest_num, latest_type, pick, is_win))

                # 6) now delete checking message
                if state.active.checking_msg_id:
                    await safe_delete(bot, state.active_target, state.active.checking_msg_id)

                # mark resolved & clear
                state.active.resolved = True
                state.last_resolved_issue = latest_issue
                state.active = None

                resolved_this_tick = True

                # stop after wins
                if state.wins >= state.stop_after_wins:
                    await stop_session(bot, reason="win_target_reached")
                    break

                # graceful stop after a win
                if state.graceful_stop_requested and is_win:
                    await stop_session(bot, reason="graceful_done")
                    break

        # 2) SIGNAL GENERATION
        if (not state.active) and is_safe_time and (not resolved_this_tick):
            if state.last_signal_issue != current_period:

                if state.streak_loss >= MAX_RECOVERY_STEPS:
                    await send_to_target(bot, "🧊 <b>SAFETY STOP</b>\n<i>Recovery limit reached.</i>")
                    await stop_session(bot, reason="max_steps")
                    break

                pred = state.engine.get_pattern_signal(state.streak_loss)
                conf = state.engine.calc_confidence(state.streak_loss)

                # 1) prediction sticker
                await send_sticker_target(bot, STICKERS["PRED_BIG"] if pred == "BIG" else STICKERS["PRED_SMALL"])

                # 2) prediction message (with clickable links)
                await send_to_target(bot, signal_text(current_period, pred, conf))

                # 3) checking message (with timer + clickable links)
                checking_mid = None
                try:
                    m = await bot.send_message(
                        state.active_target,
                        (
                            "🕛 <b>RESULT CHECKING...</b>\n"
                            f"📄 <b>PERIOD:</b> <code>{current_period}</code>\n"
                            f"🕒 <b>{now_bd_str()}</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"{footer_links_html()}"
                        ),
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                    checking_mid = m.message_id
                except Exception:
                    pass

                bet = ActiveBet(predicted_issue=current_period, pick=pred, checking_msg_id=checking_mid)
                if checking_mid:
                    bet.timer_task = asyncio.create_task(run_checking_timer(bot, state.active_target, checking_mid, current_period))

                state.active = bet
                state.last_signal_issue = current_period

        await asyncio.sleep(0.6)

# =========================
# auto scheduler
# =========================
async def scheduler_loop(app: Application):
    while True:
        try:
            now = now_bd()
            in_window = is_now_in_any_window(now, state.custom_window)
            if state.auto_schedule_enabled:
                if in_window and (not state.running):
                    await start_session(app.bot, started_by_schedule=True)
                    app.create_task(engine_loop(app, state.session_id))
                elif (not in_window) and state.running and state.started_by_schedule:
                    await stop_session(app.bot, reason="schedule_end")
        except Exception as e:
            print("Scheduler error:", e)
        await asyncio.sleep(10)

# =========================
# input parsers
# =========================
def parse_time_12h_token(t: str) -> Optional[int]:
    s = t.strip().upper().replace(" ", "")
    try:
        dt = datetime.strptime(s, "%I:%M%p")
        return dt.hour * 60 + dt.minute
    except Exception:
        return None

def parse_time_range(text: str) -> Optional[Tuple[int, int]]:
    s = text.strip().replace("—", "-").replace("–", "-")
    if "-" not in s:
        return None
    a, b = s.split("-", 1)
    start = parse_time_12h_token(a)
    end = parse_time_12h_token(b)
    if start is None or end is None:
        return None
    if end <= start:
        return None
    return (start, end)

# =========================
# commands
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.expected_password = await get_live_password()
    state.unlocked = False
    state.waiting_for = None
    state.admin_chat_id = update.effective_chat.id
    state.menu_mode = "CHOOSE_CHANNEL"
    await update.message.reply_text("🔒 <b>SYSTEM LOCKED</b>\n✅ Password দিন:", parse_mode=ParseMode.HTML)

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.admin_chat_id = update.effective_chat.id
    if not state.unlocked:
        await update.message.reply_text("🔒 <b>LOCKED</b>\n/start দিয়ে unlock করো।", parse_mode=ParseMode.HTML)
        return
    await render_panel(context.bot)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    state.admin_chat_id = update.effective_chat.id

    # unlock
    if not state.unlocked:
        state.expected_password = await get_live_password()
        if txt == state.expected_password:
            state.unlocked = True
            state.waiting_for = None
            state.menu_mode = "CHOOSE_CHANNEL"
            await update.message.reply_text("✅ <b>UNLOCKED</b>", parse_mode=ParseMode.HTML)
            await render_panel(context.bot)
        else:
            await update.message.reply_text("❌ <b>WRONG PASSWORD</b>", parse_mode=ParseMode.HTML)
        return

    # menu inputs
    if state.waiting_for == "TIME":
        rng = parse_time_range(txt)
        if rng:
            state.custom_window = rng
            state.waiting_for = None
        await render_panel(context.bot)
        return

    if state.waiting_for == "WINS":
        if txt.isdigit():
            n = int(txt)
            if 1 <= n <= 200:
                state.stop_after_wins = n
                state.waiting_for = None
        await render_panel(context.bot)
        return

    if state.waiting_for == "SENDMSG":
        state.waiting_for = None
        if state.running:
            state.queued_messages.append(txt)
        else:
            await send_plain_to_target(context.bot, txt)
        await render_panel(context.bot)
        return

# =========================
# callbacks
# =========================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = (q.data or "").strip()

    try:
        await q.answer("✅", cache_time=0)
    except Exception:
        pass

    if not state.unlocked:
        return

    if data.startswith("CHSEL:"):
        try:
            state.active_target = int(data.split(":")[1])
            state.menu_mode = "CHANNEL_PANEL"
            state.waiting_for = None
        except Exception:
            pass
        await render_panel(context.bot)
        return

    if data == "BACK_CHANNELS":
        state.menu_mode = "CHOOSE_CHANNEL"
        state.waiting_for = None
        await render_panel(context.bot)
        return

    if data == "REFRESH_PANEL":
        await render_panel(context.bot)
        return

    if data == "TOGGLE_AUTO":
        state.auto_schedule_enabled = not state.auto_schedule_enabled
        await render_panel(context.bot)
        return

    if data == "SET_TIME":
        state.waiting_for = "TIME"
        await render_panel(context.bot)
        return

    if data == "SET_WINS":
        state.waiting_for = "WINS"
        await render_panel(context.bot)
        return

    if data == "SENDMSG":
        state.waiting_for = "SENDMSG"
        await render_panel(context.bot)
        return

    if data == "START:1M":
        if state.running:
            await stop_session(context.bot, reason="restart_manual")
        await start_session(context.bot, started_by_schedule=False)
        context.application.create_task(engine_loop(context.application, state.session_id))
        await render_panel(context.bot)
        return

    if data == "STOP:FORCE":
        if state.running:
            await stop_session(context.bot, reason="force")
        await render_panel(context.bot)
        return

    if data == "STOP:GRACEFUL":
        state.graceful_stop_requested = True
        await render_panel(context.bot)
        return

# =========================
# post init
# =========================
async def post_init(app: Application):
    app.create_task(scheduler_loop(app))

# =========================
# main
# =========================
def main():
    logging.basicConfig(level=logging.WARNING)
    keep_alive()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("panel", cmd_panel))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
