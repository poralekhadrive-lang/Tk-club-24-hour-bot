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
BOT_TOKEN = "8456002611:AAHI8s74CeabkdjLHMZ3zDISBS8_0ZyPq3s"  # <-- তোমার টোকেন
BRAND_NAME = "⚡ 𝗧𝗞 𝗖𝗟𝗨𝗕 𝗠𝗔𝗥𝗨𝗙 𝗩𝗜𝗣 𝗦𝗜𝗚𝗡𝗔𝗟 ⚡"
OWNER_USERNAME = "@OWNER_MARUF_TOP"

REG_LINK = "https://tkclub2.com/#/register?invitationCode=42584207677"
CHANNEL_LINK = "https://t.me/Vip_signal_group_11"

TARGETS = {
    "MAIN_GROUP": -1003263928753,
    "VIP": -1002892329434,
    "PUBLIC": -1003034758076,  # ✅ updated
}

API_URL = "https://api880.inpay88.net/api/webapi/GetNoaverageEmerdList"
BD_TZ = timezone(timedelta(hours=6))

PASSWORD_SHEET_ID = "1foCsja-2HRi8HHjnMP8CyheaLOwk-ZiJ7a5uqs9khvo"
PASSWORD_SHEET_GID = "0"
PASSWORD_FALLBACK = "2222"

MAX_RECOVERY_STEPS = 8
FETCH_TIMEOUT = 6.0

# =========================
# DEFAULT AUTO WINDOWS (kept)
# =========================
AUTO_WINDOWS = [
    ("21:00", "21:30"),
    ("23:00", "23:30"),
    ("10:00", "10:30"),
    ("12:00", "12:30"),
    ("15:00", "15:30"),
    ("19:00", "19:30"),
]


def _hhmm_to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


AUTO_WINDOWS_MIN = [(_hhmm_to_minutes(a), _hhmm_to_minutes(b)) for a, b in AUTO_WINDOWS]


def now_bd() -> datetime:
    return datetime.now(BD_TZ)


def now_bd_str() -> str:
    return now_bd().strftime("%I:%M:%S %p").lstrip("0")


def fmt_12h(dt: datetime) -> str:
    return dt.strftime("%I:%M %p").lstrip("0")


def fmt_12h_from_minutes(mins: int) -> str:
    h = mins // 60
    m = mins % 60
    dt = datetime(2000, 1, 1, h, m, tzinfo=BD_TZ)
    return fmt_12h(dt)


def calc_current_1m_period(now: datetime) -> str:
    date_str = now.strftime("%Y%m%d")
    total_slots = (now.hour * 60) + now.minute + 1
    return f"{date_str}01{total_slots:04d}"


def is_now_in_any_window(now: datetime, custom_window: Optional[Tuple[int, int]]) -> bool:
    mins = now.hour * 60 + now.minute
    windows = [custom_window] if custom_window else AUTO_WINDOWS_MIN
    for a, b in windows:
        if a <= mins < b:
            return True
    return False


def next_window_start(now: datetime, custom_window: Optional[Tuple[int, int]]) -> str:
    mins_now = now.hour * 60 + now.minute

    if custom_window:
        s = custom_window[0]
        h = s // 60
        m = s % 60
        dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if (h * 60 + m) <= mins_now:
            dt = dt + timedelta(days=1)
        return fmt_12h(dt)

    starts = sorted([_hhmm_to_minutes(a) for a, _ in AUTO_WINDOWS])
    for s in starts:
        if s > mins_now:
            return fmt_12h_from_minutes(s)
    return fmt_12h_from_minutes(starts[0])


# =========================
# STICKERS
# =========================
STICKERS = {
    # ✅ Your required pred stickers
    "PRED_BIG": "CAACAgUAAxkBAAEQYx5pfc4AATgOO5wT5AABMN-bMJl5k_RQAALhHQACDsygVwoi0Z3WbYKyOAQ",
    "PRED_SMALL": "CAACAgUAAxkBAAEQYx1pfc4AAYYby230GOERm9UbVwrbZrcAAl8ZAAKDVphXk0mOoe8u1Zc4BA",
    # ✅ Session start/close
    "SESSION_START": "CAACAgUAAxkBAAEQYyFpfc4wbxDAkFww3cpExFCaz1iDbQACoB0AAhxruVZktiP7rGZdATgE",
    "SESSION_CLOSE": "CAACAgUAAxkBAAEQYyJpfc4wO83n6lkaDSMVxxFDzq6erwACaB4AAkbvuFbNxjX-zft8RzgE",
    # ✅ win/loss + super win
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
# FLASK KEEP ALIVE
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
# PREDICTION ENGINE (YOUR MATRIX)
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
        base = random.randint(94, 99)
        return max(40, base - (streak_loss * 7))

    def get_pattern_signal(self, current_streak_loss):
        if len(self.history) < 5:
            return random.choice(["BIG", "SMALL"])

        h = self.history
        last = h[0]
        prev1 = h[1]
        prev2 = h[2]

        prediction = None

        # PHASE 1
        if last == prev1 == prev2:
            prediction = last
        elif last != prev1 and prev1 != prev2:
            prediction = "SMALL" if last == "BIG" else "BIG"
        elif prev1 == prev2 and last != prev1:
            prediction = last
        else:
            prediction = last

        # PHASE 2
        if 2 <= current_streak_loss <= 3:
            prediction = "SMALL" if prediction == "BIG" else "BIG"

        # PHASE 3
        if current_streak_loss >= 4:
            prediction = last

        self.last_prediction = prediction
        return prediction

# =========================
# TIMER (rotating clock)
# =========================
CLOCK_FRAMES = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]

async def run_checking_timer(bot, chat_id: int, msg_id: int, issue: str):
    i = 0
    try:
        while state.running and state.active and (state.active.predicted_issue == issue):
            clock = CLOCK_FRAMES[i % len(CLOCK_FRAMES)]
            i += 1
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=f"{clock} <b>RESULT CHECKING...</b>\n🧾 <b>PERIOD:</b> <code>{issue}</code>\n🕒 <b>{now_bd_str()}</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                break
            await asyncio.sleep(2.0)
    except asyncio.CancelledError:
        return

# =========================
# STATE
# =========================
@dataclass
class ActiveBet:
    predicted_issue: str
    pick: str
    checking_msg_ids: Dict[int, int] = field(default_factory=dict)
    timer_tasks: Dict[int, asyncio.Task] = field(default_factory=dict)

@dataclass
class BotState:
    # session
    running: bool = False
    session_id: int = 0
    engine: PredictionEngine = field(default_factory=PredictionEngine)
    active: Optional[ActiveBet] = None
    last_signal_issue: Optional[str] = None

    # stats
    wins: int = 0
    losses: int = 0
    streak_win: int = 0
    streak_loss: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

    # lock
    unlocked: bool = False
    expected_password: str = PASSWORD_FALLBACK

    # menu system
    menu_mode: str = "CHOOSE_CHANNEL"  # CHOOSE_CHANNEL | CHANNEL_PANEL
    active_target: int = TARGETS["MAIN_GROUP"]  # current channel in control

    # settings per "current target" (simple single set, applies to active target)
    auto_schedule_enabled: bool = True
    started_by_schedule: bool = False
    custom_window: Optional[Tuple[int, int]] = None
    stop_after_wins: int = 40

    # input modes
    waiting_for: Optional[str] = None  # None | TIME | WINS | SENDMSG

    # send-message queue
    queued_messages: List[str] = field(default_factory=list)

    # stop
    graceful_stop_requested: bool = False
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)

state = BotState()

def reset_stats():
    state.wins = 0
    state.losses = 0
    state.streak_win = 0
    state.streak_loss = 0
    state.max_win_streak = 0
    state.max_loss_streak = 0

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
# INPUT PARSERS
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
# BROADCAST HELPERS
# =========================
async def safe_delete(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

async def send_to_target(bot, text: str, target_id: int):
    """
    ✅ No parse_mode by default so user message (emoji/custom) stays as-is.
    """
    try:
        await bot.send_message(
            target_id,
            text,
            disable_web_page_preview=False,
        )
    except Exception:
        # fallback with HTML disabled preview
        try:
            await bot.send_message(target_id, text, disable_web_page_preview=True)
        except Exception:
            pass

async def broadcast_message(bot, text: str):
    await send_to_target(bot, text, state.active_target)

async def broadcast_sticker(bot, sticker_id: str):
    try:
        await bot.send_sticker(state.active_target, sticker_id)
    except Exception:
        pass

# =========================
# PREMIUM SIGNAL MESSAGES
# =========================
def pick_badge(pick: str) -> str:
    return "🟢 <b>BIG</b>" if pick == "BIG" else "🔴 <b>SMALL</b>"

def format_signal(issue: str, pick: str, conf: int) -> str:
    return (
        f"{BRAND_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 PERIOD: {issue}\n"
        f"🎯 ENTRY: {'BIG' if pick=='BIG' else 'SMALL'}\n"
        f"✨ CONFIDENCE: {conf}%\n"
        f"🧠 RECOVERY: {state.streak_loss}/{MAX_RECOVERY_STEPS}\n"
        f"🕒 TIME: {now_bd_str()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Open Account: {REG_LINK}\n"
        f"📣 VIP: {CHANNEL_LINK}\n"
        f"👤 Owner: {OWNER_USERNAME}"
    )

def format_result(issue: str, res_num: str, res_type: str, pick: str, is_win: bool) -> str:
    head = "✅ WIN CONFIRMED" if is_win else "❌ LOSS CONFIRMED"
    return (
        f"{head}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 PERIOD: {issue}\n"
        f"🎰 RESULT: {res_num} ({res_type})\n"
        f"🎯 YOUR PICK: {pick}\n"
        f"📊 W: {state.wins} | L: {state.losses}\n"
        f"🕒 {now_bd_str()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📣 VIP: {CHANNEL_LINK}"
    )

def format_summary() -> str:
    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0
    return (
        "🛑 SESSION SUMMARY\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 TOTAL: {total}\n"
        f"✅ WIN: {state.wins}\n"
        f"❌ LOSS: {state.losses}\n"
        f"🎯 WIN RATE: {wr:.1f}%\n"
        f"🔥 MAX WIN STREAK: {state.max_win_streak}\n"
        f"🧊 MAX LOSS STREAK: {state.max_loss_streak}\n"
        f"🕒 CLOSED: {now_bd_str()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 OWNER: {OWNER_USERNAME}"
    )

def after_close_review_message(next_time_12h: str) -> str:
    return (
        "⏺সিগন্যাল কেমন হলো? অবশ্যই এখানে রিভিউ দিবেন 💋\n\n"
        f"{OWNER_USERNAME}  ❤️\n\n"
        f"এবং পরবর্তী সিগন্যাল হবে {next_time_12h} ⏰🔥\n\n"
        f"{REG_LINK}\n\n"
        "অ্যাকাউন্ট খুলে ইনবক্সে ইউআইডি দিন। এবং মিনিমাম 300 টাকা ডিপোজিট করে "
        "বট সিগন্যাল উপভোগ করুন এবং আনলিমিটেড হ্যাক নিন 🌟✅\n\n"
        f"{OWNER_USERNAME} ❤️"
    )

# =========================
# MENUS
# =========================
def channel_selector_text() -> str:
    return (
        "📌 <b>CHOOSE CHANNEL</b>\n"
        "যেই গ্রুপ/চ্যানেলে চালাতে চাও সেটায় ক্লিক করো ✅\n\n"
        "⚠️ এরপর যে মেনু আসবে—সেগুলো শুধু ওই চ্যানেলের জন্য কাজ করবে।"
    )

def channel_selector_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ MAIN GROUP", callback_data=f"CHSEL:{TARGETS['MAIN_GROUP']}")],
        [InlineKeyboardButton("✅ VIP", callback_data=f"CHSEL:{TARGETS['VIP']}"),
         InlineKeyboardButton("✅ PUBLIC", callback_data=f"CHSEL:{TARGETS['PUBLIC']}")],
    ])

def channel_panel_text() -> str:
    target_name = [k for k,v in TARGETS.items() if v == state.active_target]
    target_name = target_name[0] if target_name else "TARGET"

    custom = (
        f"{fmt_12h_from_minutes(state.custom_window[0])}-{fmt_12h_from_minutes(state.custom_window[1])}"
        if state.custom_window else "Not Set"
    )

    running = "🟢 RUNNING" if state.running else "🔴 STOPPED"
    return (
        f"🎛 <b>{target_name} CONTROL PANEL</b>\n"
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
    )

def channel_panel_markup() -> InlineKeyboardMarkup:
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
# SESSION CONTROL
# =========================
async def flush_queued_messages(bot):
    if not state.queued_messages:
        return
    msgs = state.queued_messages[:]
    state.queued_messages.clear()
    for m in msgs:
        await send_to_target(bot, m, state.active_target)
        await asyncio.sleep(0.7)

async def stop_session(bot, reason: str = "manual"):
    state.session_id += 1
    state.running = False
    state.stop_event.set()

    # stop timers + delete checking
    if state.active:
        for _, task in (state.active.timer_tasks or {}).items():
            try:
                task.cancel()
            except Exception:
                pass
        for cid, mid in (state.active.checking_msg_ids or {}).items():
            await safe_delete(bot, cid, mid)

    # summary
    try:
        await bot.send_message(state.active_target, format_summary(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        await send_to_target(bot, format_summary(), state.active_target)

    # close sticker
    await broadcast_sticker(bot, STICKERS["SESSION_CLOSE"])

    # ✅ send queued messages AFTER session end
    await flush_queued_messages(bot)

    # next signal info
    nxt = next_window_start(now_bd(), state.custom_window)
    await send_to_target(bot, after_close_review_message(nxt), state.active_target)

    state.active = None
    state.graceful_stop_requested = False
    state.started_by_schedule = False

async def start_session(bot, started_by_schedule: bool):
    state.session_id += 1
    state.running = True
    state.stop_event.clear()
    state.graceful_stop_requested = False
    state.engine = PredictionEngine()
    state.active = None
    state.last_signal_issue = None
    state.started_by_schedule = started_by_schedule
    reset_stats()

    await broadcast_sticker(bot, STICKERS["SESSION_START"])

# =========================
# ENGINE LOOP
# =========================
async def engine_loop(app: Application, my_session: int):
    bot = app.bot

    while state.running and state.session_id == my_session:
        if state.stop_event.is_set():
            break

        now = now_bd()
        sec = now.second
        current_period = calc_current_1m_period(now)

        is_safe_time = (5 <= sec <= 40)
        resolved_this_tick = False

        # 1) RESULT PROCESS FIRST
        latest_data = await fetch_latest_issue()
        if latest_data:
            state.engine.update_history(latest_data)
            latest_issue = str(latest_data.get("issueNumber"))
            latest_num = str(latest_data.get("number"))
            latest_type = "BIG" if int(latest_data.get("number")) >= 5 else "SMALL"

            if state.active and state.active.predicted_issue == latest_issue:
                pick = state.active.pick
                is_win = (pick == latest_type)

                # stop timers + delete checking
                for _, task in (state.active.timer_tasks or {}).items():
                    try:
                        task.cancel()
                    except Exception:
                        pass
                for cid, mid in (state.active.checking_msg_ids or {}).items():
                    await safe_delete(bot, cid, mid)

                if is_win:
                    state.wins += 1
                    state.streak_win += 1
                    state.streak_loss = 0
                    state.max_win_streak = max(state.max_win_streak, state.streak_win)

                    await broadcast_sticker(bot, STICKERS["WIN_ALWAYS"])
                    if state.streak_win in STICKERS["SUPER_WIN"]:
                        await broadcast_sticker(bot, STICKERS["SUPER_WIN"][state.streak_win])
                    else:
                        await broadcast_sticker(bot, random.choice(STICKERS["WIN_POOL"]))
                    await broadcast_sticker(bot, STICKERS["WIN_BIG"] if latest_type == "BIG" else STICKERS["WIN_SMALL"])
                    await broadcast_sticker(bot, STICKERS["WIN_ANY"])
                    await broadcast_sticker(bot, STICKERS["WIN_EXTRA"])
                else:
                    state.losses += 1
                    state.streak_loss += 1
                    state.streak_win = 0
                    state.max_loss_streak = max(state.max_loss_streak, state.streak_loss)
                    await broadcast_sticker(bot, STICKERS["LOSS"])

                await send_to_target(bot, format_result(latest_issue, latest_num, latest_type, pick, is_win), state.active_target)

                state.active = None
                resolved_this_tick = True

                # ✅ stop after wins target
                if state.wins >= state.stop_after_wins:
                    await stop_session(bot, reason="win_target_reached")
                    break

                if state.graceful_stop_requested and is_win:
                    await stop_session(bot, reason="graceful_done")
                    break

        # 2) SIGNAL GENERATION
        if (not state.active) and is_safe_time and (not resolved_this_tick):
            if state.last_signal_issue != current_period:
                if state.streak_loss >= MAX_RECOVERY_STEPS:
                    await send_to_target(bot, "🧊 SAFETY STOP\nRecovery limit reached.", state.active_target)
                    await stop_session(bot, reason="max_steps")
                    break

                pred = state.engine.get_pattern_signal(state.streak_loss)
                conf = state.engine.calc_confidence(state.streak_loss)

                await broadcast_sticker(bot, STICKERS["PRED_BIG"] if pred == "BIG" else STICKERS["PRED_SMALL"])
                await send_to_target(bot, format_signal(current_period, pred, conf), state.active_target)

                checking_ids = {}
                timer_tasks = {}
                try:
                    m = await bot.send_message(
                        state.active_target,
                        f"🕛 <b>RESULT CHECKING...</b>\n🧾 <b>PERIOD:</b> <code>{current_period}</code>\n🕒 <b>{now_bd_str()}</b>",
                        parse_mode=ParseMode.HTML
                    )
                    checking_ids[state.active_target] = m.message_id
                    timer_tasks[state.active_target] = asyncio.create_task(run_checking_timer(bot, state.active_target, m.message_id, current_period))
                except Exception:
                    pass

                state.active = ActiveBet(
                    predicted_issue=current_period,
                    pick=pred,
                    checking_msg_ids=checking_ids,
                    timer_tasks=timer_tasks
                )
                state.last_signal_issue = current_period

        await asyncio.sleep(0.6)

# =========================
# AUTO SCHEDULER LOOP
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
# COMMANDS
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.expected_password = await get_live_password()
    state.unlocked = False
    state.waiting_for = None
    state.menu_mode = "CHOOSE_CHANNEL"
    await update.message.reply_text("🔒 <b>SYSTEM LOCKED</b>\n✅ Password দিন:", parse_mode=ParseMode.HTML)

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.unlocked:
        await update.message.reply_text("🔒 <b>LOCKED</b>\n/start দিয়ে unlock করো।", parse_mode=ParseMode.HTML)
        return

    # show channel selector always
    state.menu_mode = "CHOOSE_CHANNEL"
    await update.message.reply_text(channel_selector_text(), parse_mode=ParseMode.HTML, reply_markup=channel_selector_markup())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    # 1) Unlock flow
    if not state.unlocked:
        state.expected_password = await get_live_password()
        if txt == state.expected_password:
            state.unlocked = True
            state.waiting_for = None
            state.menu_mode = "CHOOSE_CHANNEL"
            await update.message.reply_text("✅ <b>UNLOCKED</b>\nএখন চ্যানেল সিলেক্ট করো ✅", parse_mode=ParseMode.HTML)
            await update.message.reply_text(channel_selector_text(), parse_mode=ParseMode.HTML, reply_markup=channel_selector_markup())
        else:
            await update.message.reply_text("❌ <b>WRONG PASSWORD</b>", parse_mode=ParseMode.HTML)
        return

    # 2) Waiting inputs (per menu)
    if state.waiting_for == "TIME":
        rng = parse_time_range(txt)
        if not rng:
            await update.message.reply_text("❌ ফরম্যাট ভুল!\n✅ এভাবে দিন: <b>10:00PM-10:30PM</b>", parse_mode=ParseMode.HTML)
            return
        state.custom_window = rng
        state.waiting_for = None
        await update.message.reply_text(
            f"✅ <b>TIME SET</b> → <b>{fmt_12h_from_minutes(rng[0])}-{fmt_12h_from_minutes(rng[1])}</b>",
            parse_mode=ParseMode.HTML
        )
        await update.message.reply_text(channel_panel_text(), parse_mode=ParseMode.HTML, reply_markup=channel_panel_markup())
        return

    if state.waiting_for == "WINS":
        if not txt.isdigit():
            await update.message.reply_text("❌ শুধু সংখ্যা দিন! উদাহরণ: <b>40</b>", parse_mode=ParseMode.HTML)
            return
        n = int(txt)
        if n < 1 or n > 200:
            await update.message.reply_text("❌ 1 থেকে 200 এর মধ্যে দিন!", parse_mode=ParseMode.HTML)
            return
        state.stop_after_wins = n
        state.waiting_for = None
        await update.message.reply_text(f"✅ <b>WIN TARGET SET</b> → <b>{n}</b>", parse_mode=ParseMode.HTML)
        await update.message.reply_text(channel_panel_text(), parse_mode=ParseMode.HTML, reply_markup=channel_panel_markup())
        return

    if state.waiting_for == "SENDMSG":
        # ✅ queue if running, else send instantly
        state.waiting_for = None
        if state.running:
            state.queued_messages.append(txt)
            await update.message.reply_text("✅ OK! সেশন শেষ হলে মেসেজটা অটো পাঠানো হবে ✅", parse_mode=ParseMode.HTML)
        else:
            await send_to_target(context.bot, txt, state.active_target)
            await update.message.reply_text("✅ OK! মেসেজ পাঠানো হয়েছে ✅", parse_mode=ParseMode.HTML)

        await update.message.reply_text(channel_panel_text(), parse_mode=ParseMode.HTML, reply_markup=channel_panel_markup())
        return

# =========================
# CALLBACKS (ALWAYS RESPONDS)
# =========================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = (q.data or "").strip()

    # instant ack
    try:
        await q.answer("✅ OK", cache_time=0)
    except Exception:
        pass

    async def safe_edit(text: str, markup: InlineKeyboardMarkup):
        try:
            await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except Exception:
            # fallback send new
            try:
                await context.bot.send_message(update.effective_chat.id, text, parse_mode=ParseMode.HTML, reply_markup=markup)
            except Exception:
                pass

    if not state.unlocked:
        try:
            await q.answer("🔒 LOCKED", show_alert=True, cache_time=0)
        except Exception:
            pass
        return

    # --- Channel select screen ---
    if data.startswith("CHSEL:"):
        try:
            target = int(data.split(":")[1])
            state.active_target = target
            state.menu_mode = "CHANNEL_PANEL"
            state.waiting_for = None
        except Exception:
            pass
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "BACK_CHANNELS":
        state.menu_mode = "CHOOSE_CHANNEL"
        state.waiting_for = None
        await safe_edit(channel_selector_text(), channel_selector_markup())
        return

    # --- Channel panel buttons ---
    if data == "REFRESH_PANEL":
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "TOGGLE_AUTO":
        state.auto_schedule_enabled = not state.auto_schedule_enabled
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "SET_TIME":
        state.waiting_for = "TIME"
        # prompt message (always new message)
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                "🕒 <b>SELECT TIME</b>\nএই মেসেজে রিপ্লাই দাও:\n<b>10:00PM-10:30PM</b>\n\n✅ Example:\n<code>06:00PM-06:30PM</code>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "SET_WINS":
        state.waiting_for = "WINS"
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                "🏆 <b>SELECT WIN TARGET</b>\nএই মেসেজে শুধু সংখ্যা লিখে রিপ্লাই দাও:\nExample: <b>40</b>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "SENDMSG":
        state.waiting_for = "SENDMSG"
        try:
            await context.bot.send_message(
                update.effective_chat.id,
                "📨 <b>SEND MESSAGE</b>\nএই মেসেজে রিপ্লাই দিয়ে তোমার মেসেজ লিখো।\n\n"
                "✅ যদি সেশন চলতে থাকে → সেশন শেষ হলে যাবে\n"
                "✅ সেশন না চললে → সাথে সাথে যাবে",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "START:1M":
        if state.running:
            await stop_session(context.bot, reason="restart_manual")
        await start_session(context.bot, started_by_schedule=False)
        context.application.create_task(engine_loop(context.application, state.session_id))
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "STOP:FORCE":
        if state.running:
            await stop_session(context.bot, reason="force")
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    if data == "STOP:GRACEFUL":
        state.graceful_stop_requested = True
        await safe_edit(channel_panel_text(), channel_panel_markup())
        return

    await safe_edit(channel_panel_text(), channel_panel_markup())

# =========================
# POST INIT
# =========================
async def post_init(app: Application):
    app.create_task(scheduler_loop(app))

# =========================
# MAIN
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
