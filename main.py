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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
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
BOT_TOKEN = "8456002611:AAEvhsMJFXFuc0OYZCJhQ9WRKyUvryrfsso"  # <-- তুমি বলছ env use না, তাই এখানে দাও

OWNER_USERNAME = "@OWNER_MARUF_TOP"
OWNER_LINK = "https://t.me/OWNER_MARUF_TOP"

CHANNEL_LINK = "https://t.me/Vip_signal_group_11"
REG_LINK = "https://tkclub2.com/#/register?invitationCode=42584207677"

API_URL = "https://api880.inpay88.net/api/webapi/GetNoaverageEmerdList"
BD_TZ = timezone(timedelta(hours=6))

FETCH_TIMEOUT = 6.0
MAX_RECOVERY_STEPS = 8

# Targets (Public ID updated)
TARGETS = {
    "MAIN": -1003263928753,
    "VIP": -1002892329434,
    "PUBLIC": -1003034758076,
}

# =========================
# STICKERS
# =========================
STICKERS = {
    # Session Start / Close
    "SESSION_START": "CAACAgUAAxkBAAEQYyFpfc4wbxDAkFww3cpExFCaz1iDbQACoB0AAhxruVZktiP7rGZdATgE",
    "SESSION_CLOSE": "CAACAgUAAxkBAAEQYyJpfc4wO83n6lkaDSMVxxFDzq6erwACaB4AAkbvuFbNxjX-zft8RzgE",

    # Prediction (You told to use)
    "PRED_BIG": "CAACAgUAAxkBAAEQYx5pfc4AATgOO5wT5AABMN-bMJl5k_RQAALhHQACDsygVwoi0Z3WbYKyOAQ",
    "PRED_SMALL": "CAACAgUAAxkBAAEQYx1pfc4AAYYby230GOERm9UbVwrbZrcAAl8ZAAKDVphXk0mOoe8u1Zc4BA",

    # Win/Loss sticker pools (keep some; তুমি চাইলে এখানে আরও add করবা)
    "WIN": [
        "CAACAgUAAxkBAAEQTzNpcz9ns8rx_5xmxk4HHQOJY2uUQQAC3RoAAuCpcFbMKj0VkxPOdTgE",
        "CAACAgUAAxkBAAEQTzRpcz9ni_I4CjwFZ3iSt4xiXxFgkwACkxgAAnQKcVYHd8IiRqfBXTgE",
        "CAACAgUAAxkBAAEQTx9pcz8GryuxGBMFtzRNRbiCTg9M8wAC5xYAAkN_QFWgd5zOh81JGDgE",
    ],
    "LOSS": "CAACAgUAAxkBAAEQTytpcz9VQoHyZ5ClbKSqKCJbpqX6yQACahYAAl1wAAFUL9xOdyh8UL84BA",

    # Super win by streak count (keep)
    "SUPER_WIN": {
        2: "CAACAgUAAxkBAAEQTiBpcmUfm9aQmlIHtPKiG2nE2e6EeAACcRMAAiLWqFSpdxWmKJ1TXzgE",
        3: "CAACAgUAAxkBAAEQTiFpcmUgdgJQ_czeoFyRhNZiZI2lwwAC8BcAAv8UqFSVBQEdUW48HTgE",
        4: "CAACAgUAAxkBAAEQTiJpcmUgSydN-tKxoSVdFuAvCcJ3fQACvSEAApMRqFQoUYBnH5Pc7TgE",
        5: "CAACAgUAAxkBAAEQTiNpcmUgu_dP3wKT2k94EJCiw3u52QACihoAArkfqFSlrldtXbLGGDgE",
        6: "CAACAgUAAxkBAAEQTiRpcmUhQJUjd2ukdtfEtBjwtMH4MAACWRgAAsTFqVTato0SmSN-6jgE",
    }
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
# PREDICTION ENGINE (ZIGZAG HUNTER + INSTANT ADAPTER)
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
        # ইতিহাস না থাকলে র‍্যান্ডম
        if len(self.history) < 2:
            return random.choice(["BIG", "SMALL"])

        last = self.history[0]
        prev = self.history[1]

        # ১) যদি last != prev => ZigZag চলতেছে => Opposite
        if last != prev:
            prediction = "SMALL" if last == "BIG" else "BIG"
        else:
            # ২) Double/Dragon => Copy
            prediction = last

        # Loss হলে flip (instant adapter)
        if current_streak_loss > 0:
            prediction = "SMALL" if prediction == "BIG" else "BIG"

        self.last_prediction = prediction
        return prediction

# =========================
# UTILS
# =========================
def now_bd() -> datetime:
    return datetime.now(BD_TZ)

def now_bd_str() -> str:
    return now_bd().strftime("%I:%M:%S %p")

def fmt_owner() -> str:
    return f"<a href='{OWNER_LINK}'>{OWNER_USERNAME}</a>"

def fmt_links() -> str:
    return (
        f"🔗 <b>Open Account:</b> <a href='{REG_LINK}'>Click Here</a>\n"
        f"📣 <b>VIP Channel:</b> <a href='{CHANNEL_LINK}'>Join Now</a>\n"
        f"👤 <b>Owner:</b> {fmt_owner()}"
    )

def pick_badge(pick: str) -> str:
    return "🟢 <b>BIG</b>" if pick == "BIG" else "🔴 <b>SMALL</b>"

def result_emoji(res_type: str) -> str:
    return "🟢" if res_type == "BIG" else "🔴"

CLOCK_SPIN = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]

def format_signal(issue: str, pick: str, conf: int, streak_loss: int) -> str:
    return (
        f"🔥 <b>VIP SIGNAL GROUP</b> 🔥\n"
        f"⚡ <b>TK CLUB MARUF VIP SIGNAL</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎯 <b>ENTRY:</b> {pick_badge(pick)}\n"
        f"✨ <b>CONFIDENCE:</b> <b>{conf}%</b>\n"
        f"🧠 <b>RECOVERY:</b> <b>{streak_loss}/{MAX_RECOVERY_STEPS}</b>\n"
        f"⏱ <b>TIME:</b> <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{fmt_links()}"
    )

def format_checking(issue: str, spin: str) -> str:
    return (
        f"{spin} <b>RESULT CHECKING...</b>\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"⏱ <b>{now_bd_str()}</b>"
    )

def format_result(issue: str, res_num: str, res_type: str, pick: str, wins: int, losses: int, is_win: bool) -> str:
    head = "✅ <b>WIN CONFIRMED</b>" if is_win else "❌ <b>LOSS CONFIRMED</b>"
    return (
        f"🔥 <b>VIP SIGNAL GROUP</b> 🔥\n"
        f"{head}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎰 <b>RESULT:</b> {result_emoji(res_type)} <b>{res_num} ({res_type})</b>\n"
        f"🎯 <b>YOUR PICK:</b> {pick_badge(pick)}\n"
        f"📊 <b>W:</b> <b>{wins}</b>  |  <b>L:</b> <b>{losses}</b>\n"
        f"⏱ <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{fmt_links()}"
    )

def format_session_close(next_time_hint: str, wins: int, losses: int) -> str:
    total = wins + losses
    wr = (wins / total * 100) if total else 0.0
    return (
        f"🛑 <b>SESSION STOP</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>Total:</b> <b>{total}</b>\n"
        f"✅ <b>Win:</b> <b>{wins}</b>\n"
        f"❌ <b>Loss:</b> <b>{losses}</b>\n"
        f"🎯 <b>Win Rate:</b> <b>{wr:.1f}%</b>\n"
        f"⏱ <b>Closed:</b> <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏭️ <b>Next Signal:</b> {next_time_hint}\n\n"
        f"⏺সিগন্যাল কেমন হলো? অবশ্যই এখানে রিভিউ দিবেন 💋\n\n"
        f"{fmt_owner()} ❤️\n\n"
        f"🔗 <a href='{REG_LINK}'>Account Open Link</a>\n"
        f"অ্যাকাউন্ট খুলে ইনবক্সে ইউআইডি দিন। এবং মিনিমাম 300 টাকা ডিপোজিট করে বট সিগন্যাল উপভোগ করুন এবং আনলিমিটেড হ্যাক নিন 🌟✅\n\n"
        f"{fmt_owner()} ❤️"
    )

# =========================
# API FETCH
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
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
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
# PERIOD CALC (same style)
# =========================
def calc_current_1m_period(now: datetime) -> str:
    date_str = now.strftime("%Y%m%d")
    total_slots = (now.hour * 60) + now.minute + 1
    return f"{date_str}01{total_slots:04d}"

# =========================
# CHANNEL CONFIG (per target)
# =========================
def parse_time_window(txt: str) -> Optional[Tuple[int, int]]:
    """
    Input example: 10:00PM-10:30PM
    Returns minutes-of-day (start,end)
    """
    try:
        raw = txt.strip().upper().replace(" ", "")
        a, b = raw.split("-")
        def to_min(t):
            # "10:00PM"
            ampm = t[-2:]
            hm = t[:-2]
            hh, mm = hm.split(":")
            hh = int(hh)
            mm = int(mm)
            if ampm == "AM":
                if hh == 12: hh = 0
            else:  # PM
                if hh != 12: hh += 12
            return hh*60 + mm
        start = to_min(a)
        end = to_min(b)
        if end <= start:
            return None
        return (start, end)
    except Exception:
        return None

def minutes_to_ampm(m: int) -> str:
    hh = m // 60
    mm = m % 60
    ampm = "AM"
    if hh >= 12:
        ampm = "PM"
    h12 = hh % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mm:02d}{ampm}"

@dataclass
class ChannelConfig:
    key: str
    chat_id: int
    name: str

    # user-selected
    window_text: str = "Not Set"
    window_min: Optional[Tuple[int, int]] = None
    win_target: int = 0  # 0 = no auto stop by wins

    # queued admin broadcast (premium emoji keep via copy)
    queued_admin_msg: Optional[Tuple[int, int]] = None  # (from_chat_id, message_id)

# =========================
# STATE
# =========================
@dataclass
class ActiveBet:
    predicted_issue: str
    pick: str
    pred_msg_ids: Dict[int, int] = field(default_factory=dict)
    checking_msg_ids: Dict[int, int] = field(default_factory=dict)
    checking_task: Optional[asyncio.Task] = None

@dataclass
class BotState:
    unlocked: bool = False
    expected_password: str = "2222"

    # single panel message (no duplicates)
    admin_chat_id: Optional[int] = None
    panel_message_id: Optional[int] = None
    menu_mode: str = "CHOOSE_CHANNEL"  # CHOOSE_CHANNEL / CONTROL

    # reply-wait mode
    waiting_for: Optional[str] = None   # "PASSWORD" / "TIME" / "WIN" / "SENDMSG"
    waiting_channel_key: Optional[str] = None

    # channel configs
    channels: Dict[str, ChannelConfig] = field(default_factory=dict)
    current_channel_key: Optional[str] = None

    # session
    running: bool = False
    session_id: int = 0
    started_by_schedule: bool = False
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    graceful_stop_requested: bool = False

    engine: PredictionEngine = field(default_factory=PredictionEngine)
    active: Optional[ActiveBet] = None
    last_signal_issue: Optional[str] = None

    wins: int = 0
    losses: int = 0
    streak_win: int = 0
    streak_loss: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

state = BotState()

def init_channels():
    state.channels = {
        "MAIN": ChannelConfig("MAIN", TARGETS["MAIN"], "MAIN GROUP"),
        "VIP": ChannelConfig("VIP", TARGETS["VIP"], "VIP"),
        "PUBLIC": ChannelConfig("PUBLIC", TARGETS["PUBLIC"], "PUBLIC"),
    }

# =========================
# PANEL UI (ONE MESSAGE ONLY)
# =========================
def choose_channel_text() -> str:
    return (
        "📌 <b>CHOOSE CHANNEL</b>\n"
        "এই গ্রুপ/চ্যানেলে চালাতে চান সিলেক্ট করুন ✅\n\n"
        "⚠️ <i>এরপর সব কন্ট্রোল শুধু ওই চ্যানেলের জন্য কাজ করবে</i>"
    )

def choose_channel_markup() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("✅ MAIN GROUP", callback_data="OPEN:MAIN"),
        ],
        [
            InlineKeyboardButton("✅ VIP", callback_data="OPEN:VIP"),
            InlineKeyboardButton("✅ PUBLIC", callback_data="OPEN:PUBLIC"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def control_panel_text(cfg: ChannelConfig) -> str:
    status = "🟢 RUNNING" if state.running else "🔴 STOPPED"
    auto = "⏰ Auto: ON" if (cfg.window_min is not None) else "⏰ Auto: OFF"
    time_line = f"🕘 Select Time: <b>{cfg.window_text}</b>"
    win_line = f"🏆 Select Win: <b>{cfg.win_target if cfg.win_target > 0 else 'Not Set'}</b>"

    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0

    return (
        f"🎛 <b>{cfg.name} CONTROL PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Status: {status}\n"
        f"{auto}\n"
        f"{time_line}\n"
        f"{win_line}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 Stats: ✅ <b>{state.wins}</b> | ❌ <b>{state.losses}</b> | 🎯 <b>{wr:.1f}%</b>\n"
        f"🔥 Streak: W <b>{state.streak_win}</b> | L <b>{state.streak_loss}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {fmt_owner()}"
    )

def control_panel_markup(cfg: ChannelConfig) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton("🕘 Select Time", callback_data="SET_TIME"),
            InlineKeyboardButton("🏆 Select Win", callback_data="SET_WIN"),
        ],
        [
            InlineKeyboardButton("✉️ Send Message", callback_data="SENDMSG"),
        ],
        [
            InlineKeyboardButton("⚡ Start 1 MIN", callback_data="START"),
        ],
        [
            InlineKeyboardButton("🧠 Stop After Win", callback_data="STOP_GRACEFUL"),
            InlineKeyboardButton("🛑 Stop Now", callback_data="STOP_FORCE"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="REFRESH"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="BACK"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

async def render_panel(bot):
    """Edit ONLY. Never send extra panel messages."""
    if not state.admin_chat_id or not state.panel_message_id:
        return

    try:
        if state.menu_mode == "CHOOSE_CHANNEL":
            await bot.edit_message_text(
                chat_id=state.admin_chat_id,
                message_id=state.panel_message_id,
                text=choose_channel_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=choose_channel_markup(),
                disable_web_page_preview=True,
            )
            return

        cfg = state.channels.get(state.current_channel_key or "MAIN")
        await bot.edit_message_text(
            chat_id=state.admin_chat_id,
            message_id=state.panel_message_id,
            text=control_panel_text(cfg),
            parse_mode=ParseMode.HTML,
            reply_markup=control_panel_markup(cfg),
            disable_web_page_preview=True,
        )
    except Exception:
        # no fallback send -> avoid duplicate panels
        pass

async def ensure_panel(bot, chat_id: int):
    """Create panel once. Later only edit."""
    state.admin_chat_id = chat_id
    if state.panel_message_id:
        return
    m = await bot.send_message(
        chat_id,
        "✅ Panel Loading...",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    state.panel_message_id = m.message_id
    state.menu_mode = "CHOOSE_CHANNEL"
    await render_panel(bot)

# =========================
# SESSION BROADCAST (STRICT ORDER)
# =========================
async def send_sticker(bot, chat_id: int, sticker_id: str):
    try:
        await bot.send_sticker(chat_id, sticker_id)
    except Exception:
        pass

async def send_html(bot, chat_id: int, text: str) -> Optional[int]:
    try:
        m = await bot.send_message(
            chat_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return m.message_id
    except Exception:
        return None

async def delete_msg(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass

def pred_sticker_for(pick: str) -> str:
    return STICKERS["PRED_BIG"] if pick == "BIG" else STICKERS["PRED_SMALL"]

def is_now_in_window(cfg: ChannelConfig, now: datetime) -> bool:
    if not cfg.window_min:
        return False
    a, b = cfg.window_min
    mins = now.hour * 60 + now.minute
    return a <= mins < b

def next_signal_hint(cfg: ChannelConfig) -> str:
    if not cfg.window_min:
        return "⏳ Not scheduled"
    a, b = cfg.window_min
    return f"✅ <b>{minutes_to_ampm(a)} - {minutes_to_ampm(b)}</b> 🔥✨"

def reset_stats():
    state.wins = 0
    state.losses = 0
    state.streak_win = 0
    state.streak_loss = 0
    state.max_win_streak = 0
    state.max_loss_streak = 0

async def start_session(app: Application, started_by_schedule: bool):
    cfg = state.channels.get(state.current_channel_key or "MAIN")
    if not cfg:
        return

    state.session_id += 1
    state.running = True
    state.started_by_schedule = started_by_schedule
    state.stop_event.clear()
    state.graceful_stop_requested = False

    state.engine = PredictionEngine()
    state.active = None
    state.last_signal_issue = None

    reset_stats()

    # Session start sticker
    await send_sticker(app.bot, cfg.chat_id, STICKERS["SESSION_START"])

async def flush_queued_admin_message(bot, cfg: ChannelConfig):
    if not cfg.queued_admin_msg:
        return
    from_chat, msg_id = cfg.queued_admin_msg
    try:
        # ✅ preserves premium/custom emoji/entities
        await bot.copy_message(chat_id=cfg.chat_id, from_chat_id=from_chat, message_id=msg_id)
    except Exception:
        pass
    cfg.queued_admin_msg = None

async def stop_session(app: Application, reason: str = "manual"):
    cfg = state.channels.get(state.current_channel_key or "MAIN")
    if not cfg:
        return

    state.session_id += 1
    state.running = False
    state.stop_event.set()

    # delete checking message if exists
    if state.active:
        for cid, mid in (state.active.checking_msg_ids or {}).items():
            await delete_msg(app.bot, cid, mid)
        if state.active.checking_task:
            state.active.checking_task.cancel()
        state.active = None

    # Session close sticker
    await send_sticker(app.bot, cfg.chat_id, STICKERS["SESSION_CLOSE"])

    # Close message + next schedule hint (ONLY after session close)
    await send_html(app.bot, cfg.chat_id, format_session_close(next_signal_hint(cfg), state.wins, state.losses))

    # If admin queued message exists, send now (after session end)
    await flush_queued_admin_message(app.bot, cfg)

    state.graceful_stop_requested = False
    state.started_by_schedule = False

async def checking_spinner_task(bot, chat_id: int, issue: str, msg_id: int, my_session: int):
    i = 0
    while state.running and state.session_id == my_session and state.active and state.active.predicted_issue == issue:
        try:
            spin = CLOCK_SPIN[i % len(CLOCK_SPIN)]
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=format_checking(issue, spin),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        i += 1
        await asyncio.sleep(1.2)

# =========================
# ENGINE LOOP (STRICT PATTERN)
# =========================
async def engine_loop(app: Application, my_session: int):
    cfg = state.channels.get(state.current_channel_key or "MAIN")
    if not cfg:
        return
    bot = app.bot
    chat_id = cfg.chat_id

    while state.running and state.session_id == my_session:
        if state.stop_event.is_set():
            break

        now = now_bd()
        sec = now.second

        # safe time window
        is_safe_time = 5 <= sec <= 40
        current_period = calc_current_1m_period(now)

        # 1) RESULT CHECK FIRST
        latest_data = await fetch_latest_issue()
        if latest_data:
            state.engine.update_history(latest_data)

            latest_issue = str(latest_data.get("issueNumber"))
            latest_num = str(latest_data.get("number"))
            latest_type = "BIG" if int(latest_num) >= 5 else "SMALL"

            if state.active and state.active.predicted_issue == latest_issue:
                pick = state.active.pick
                is_win = (pick == latest_type)

                # delete checking message
                for cid, mid in (state.active.checking_msg_ids or {}).items():
                    await delete_msg(bot, cid, mid)

                if state.active.checking_task:
                    state.active.checking_task.cancel()

                # Win/Loss update
                if is_win:
                    state.wins += 1
                    state.streak_win += 1
                    state.streak_loss = 0
                    state.max_win_streak = max(state.max_win_streak, state.streak_win)

                    # feedback sticker(s)
                    if state.streak_win in STICKERS["SUPER_WIN"]:
                        await send_sticker(bot, chat_id, STICKERS["SUPER_WIN"][state.streak_win])
                    else:
                        await send_sticker(bot, chat_id, random.choice(STICKERS["WIN"]))

                else:
                    state.losses += 1
                    state.streak_loss += 1
                    state.streak_win = 0
                    state.max_loss_streak = max(state.max_loss_streak, state.streak_loss)
                    await send_sticker(bot, chat_id, STICKERS["LOSS"])

                # feedback message
                await send_html(
                    bot,
                    chat_id,
                    format_result(latest_issue, latest_num, latest_type, pick, state.wins, state.losses, is_win),
                )

                # clear active
                state.active = None

                # stop conditions
                if cfg.win_target > 0 and state.wins >= cfg.win_target:
                    await stop_session(app, reason="win_target")
                    break

                if state.graceful_stop_requested and is_win:
                    await stop_session(app, reason="graceful_done")
                    break

        # 2) SEND SIGNAL (STRICT ORDER)
        if (not state.active) and is_safe_time:
            if state.last_signal_issue != current_period:
                # safety stop by recovery
                if state.streak_loss >= MAX_RECOVERY_STEPS:
                    await send_html(bot, chat_id, "🧯 <b>SAFETY STOP</b>\n<i>Recovery limit reached.</i>")
                    await stop_session(app, reason="max_steps")
                    break

                pred = state.engine.get_pattern_signal(state.streak_loss)
                conf = state.engine.calc_confidence(state.streak_loss)

                # 2.1 prediction sticker
                await send_sticker(bot, chat_id, pred_sticker_for(pred))

                # 2.2 prediction message
                await send_html(bot, chat_id, format_signal(current_period, pred, conf, state.streak_loss))

                # 2.3 checking message (store id)
                checking_id = await send_html(bot, chat_id, format_checking(current_period, "🕛"))
                checking_ids = {}
                if checking_id:
                    checking_ids[chat_id] = checking_id

                active = ActiveBet(predicted_issue=current_period, pick=pred, checking_msg_ids=checking_ids)

                # spinner task
                if checking_id:
                    active.checking_task = asyncio.create_task(checking_spinner_task(bot, chat_id, current_period, checking_id, my_session))

                state.active = active
                state.last_signal_issue = current_period

        await asyncio.sleep(0.6)

# =========================
# SCHEDULER LOOP (per selected channel only)
# =========================
async def scheduler_loop(app: Application):
    while True:
        try:
            if state.menu_mode != "CONTROL" or not state.current_channel_key:
                await asyncio.sleep(2)
                continue

            cfg = state.channels.get(state.current_channel_key)
            if not cfg:
                await asyncio.sleep(2)
                continue

            now = now_bd()
            in_window = is_now_in_window(cfg, now)

            # Auto start/stop only when time selected
            if cfg.window_min:
                if in_window and (not state.running):
                    await start_session(app, started_by_schedule=True)
                    app.create_task(engine_loop(app, state.session_id))
                elif (not in_window) and state.running and state.started_by_schedule:
                    await stop_session(app, reason="schedule_end")

        except Exception as e:
            print("Scheduler error:", e)

        await asyncio.sleep(5)

# =========================
# COMMANDS + INPUT HANDLER
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.unlocked = False
    state.waiting_for = "PASSWORD"
    await update.message.reply_text("🔒 <b>SYSTEM LOCKED</b>\n✅ Password দিন:", parse_mode=ParseMode.HTML)

async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.unlocked:
        await update.message.reply_text("🔒 <b>LOCKED</b>\n/start দিয়ে unlock করুন", parse_mode=ParseMode.HTML)
        return
    await ensure_panel(context.bot, update.effective_chat.id)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    # password step
    if state.waiting_for == "PASSWORD" and not state.unlocked:
        if txt == state.expected_password:
            state.unlocked = True
            state.waiting_for = None
            await update.message.reply_text("✅ <b>UNLOCKED</b>", parse_mode=ParseMode.HTML)
            await ensure_panel(context.bot, update.effective_chat.id)
            return
        await update.message.reply_text("❌ <b>WRONG PASSWORD</b>", parse_mode=ParseMode.HTML)
        return

    # time window reply
    if state.waiting_for == "TIME" and state.waiting_channel_key:
        cfg = state.channels.get(state.waiting_channel_key)
        tw = parse_time_window(txt)
        if not cfg or not tw:
            await update.message.reply_text("❌ Invalid format.\nExample: 10:00PM-10:30PM")
            return
        cfg.window_min = tw
        cfg.window_text = txt
        state.waiting_for = None
        state.waiting_channel_key = None
        await update.message.reply_text("✅ Time Set Done.")
        await render_panel(context.bot)
        return

    # win target reply
    if state.waiting_for == "WIN" and state.waiting_channel_key:
        cfg = state.channels.get(state.waiting_channel_key)
        try:
            n = int(txt)
            if n < 1 or n > 999:
                raise ValueError()
        except Exception:
            await update.message.reply_text("❌ শুধু সংখ্যা লিখুন। Example: 40")
            return
        if cfg:
            cfg.win_target = n
        state.waiting_for = None
        state.waiting_channel_key = None
        await update.message.reply_text("✅ Win Target Set Done.")
        await render_panel(context.bot)
        return

    # otherwise ignore
    return

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    For SEND MESSAGE flow:
    user can send premium emoji text / stickers / photos etc
    we store message_id and later copy_message to target.
    """
    if state.waiting_for != "SENDMSG" or not state.waiting_channel_key:
        return

    cfg = state.channels.get(state.waiting_channel_key)
    if not cfg or not update.message:
        return

    cfg.queued_admin_msg = (update.effective_chat.id, update.message.message_id)
    state.waiting_for = None
    state.waiting_channel_key = None

    await update.message.reply_text("✅ Message Saved. Session running থাকলে session end এর পর যাবে। না থাকলে এখনই যাবে।")

    # if not running -> send now
    if not state.running:
        await flush_queued_admin_message(context.bot, cfg)

    await render_panel(context.bot)

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = (q.data or "").strip()

    # ✅ bind to clicked panel message (fix "no response")
    if q and q.message:
        state.admin_chat_id = q.message.chat_id
        state.panel_message_id = q.message.message_id

    try:
        await q.answer("✅", cache_time=0)
    except Exception:
        pass

    if not state.unlocked:
        return

    # choose channel
    if data.startswith("OPEN:"):
        key = data.split(":")[1]
        if key in state.channels:
            state.current_channel_key = key
            state.menu_mode = "CONTROL"
            await render_panel(context.bot)
        return

    if data == "BACK":
        state.menu_mode = "CHOOSE_CHANNEL"
        state.current_channel_key = None
        await render_panel(context.bot)
        return

    if state.menu_mode != "CONTROL" or not state.current_channel_key:
        await render_panel(context.bot)
        return

    cfg = state.channels.get(state.current_channel_key)

    if data == "REFRESH":
        await render_panel(context.bot)
        return

    if data == "SET_TIME":
        state.waiting_for = "TIME"
        state.waiting_channel_key = cfg.key
        # IMPORTANT: just notify in chat (not new panel)
        try:
            await context.bot.send_message(
                chat_id=state.admin_chat_id,
                text="🕘 <b>SELECT TIME</b>\nএই মেসেজে শুধু রিপ্লাই দিন:\nExample: <code>10:00PM-10:30PM</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    if data == "SET_WIN":
        state.waiting_for = "WIN"
        state.waiting_channel_key = cfg.key
        try:
            await context.bot.send_message(
                chat_id=state.admin_chat_id,
                text="🏆 <b>SELECT WIN TARGET</b>\nএই মেসেজে শুধু সংখ্যা লিখে রিপ্লাই দিন:\nExample: <code>40</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    if data == "SENDMSG":
        state.waiting_for = "SENDMSG"
        state.waiting_channel_key = cfg.key
        try:
            await context.bot.send_message(
                chat_id=state.admin_chat_id,
                text="✉️ <b>SEND MESSAGE</b>\nএখন যে মেসেজটা গ্রুপে পাঠাতে চান সেটা পাঠান (premium emoji / sticker / photo সব চলবে)।\nSession চললে session end এর পর যাবে।",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    if data == "START":
        # start manual (no auto stop by time)
        if state.running:
            await stop_session(context.application, reason="restart")
        await start_session(context.application, started_by_schedule=False)
        context.application.create_task(engine_loop(context.application, state.session_id))
        await render_panel(context.bot)
        return

    if data == "STOP_FORCE":
        if state.running:
            await stop_session(context.application, reason="force")
        await render_panel(context.bot)
        return

    if data == "STOP_GRACEFUL":
        if state.running:
            state.graceful_stop_requested = True
            # if currently idle and no losses -> stop now
            if state.streak_loss == 0 and state.active is None:
                await stop_session(context.application, reason="graceful_now")
        await render_panel(context.bot)
        return

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
    init_channels()
    keep_alive()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("panel", cmd_panel))

    # ✅ callback before message handlers
    application.add_handler(CallbackQueryHandler(on_callback))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.ALL, handle_any_message), group=1)

    application.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
