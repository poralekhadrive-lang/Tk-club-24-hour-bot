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
BOT_TOKEN = "8456002611:AAHI8s74CeabkdjLHMZ3zDISBS8_0ZyPq3s"

BRAND_NAME = "⚡ 𝗧𝗞 𝗠𝗔𝗥𝗨𝗙 𝗩𝗜𝗣 𝗦𝗜𝗚𝗡𝗔𝗟 ⚡"

REG_LINK = "https://tkclub2.com/#/register?invitationCode=42584207677"
OWNER_USERNAME = "@OWNER_MARUF_TOP"
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

# =========================
# AUTO SCHEDULE (BD TIME)
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


def is_now_in_any_window(now: datetime) -> bool:
    mins = now.hour * 60 + now.minute
    for a, b in AUTO_WINDOWS_MIN:
        if a <= mins < b:
            return True
    return False


def _minutes_to_12h_str(mins: int) -> str:
    h = (mins // 60) % 24
    m = mins % 60
    dt = datetime(2000, 1, 1, h, m, tzinfo=BD_TZ)
    return dt.strftime("%I:%M %p").lstrip("0")


def _next_window_start(now: datetime) -> Tuple[str, int]:
    """
    Returns (display_string, minutes_from_now)
    Next schedule window start in BD time.
    """
    now_mins = now.hour * 60 + now.minute
    candidates = []
    for start, _end in AUTO_WINDOWS_MIN:
        delta = start - now_mins
        if delta < 0:
            delta += 24 * 60
        candidates.append((delta, start))
    candidates.sort(key=lambda x: x[0])
    delta, start_min = candidates[0]
    return _minutes_to_12h_str(start_min), delta


# =========================
# STICKERS (UPDATED BY YOU)
# =========================
STICKERS = {
    # Prediction stickers (you provided)
    "PRED_BIG": "CAACAgUAAxkBAAEQYx5pfc4AATgOO5wT5AABMN-bMJl5k_RQAALhHQACDsygVwoi0Z3WbYKyOAQ",
    "PRED_SMALL": "CAACAgUAAxkBAAEQYx1pfc4AAYYby230GOERm9UbVwrbZrcAAl8ZAAKDVphXk0mOoe8u1Zc4BA",

    # Session start/close stickers (you provided)
    "SESSION_START": "CAACAgUAAxkBAAEQYyFpfc4wbxDAkFww3cpExFCaz1iDbQACoB0AAhxruVZktiP7rGZdATgE",
    "SESSION_CLOSE": "CAACAgUAAxkBAAEQYyJpfc4wO83n6lkaDSMVxxFDzq6erwACaB4AAkbvuFbNxjX-zft8RzgE",

    # Keep your win/loss stickers (optional: you can change later)
    "WIN_ALWAYS": "CAACAgUAAxkBAAEQUTZpdFC4094KaOEdiE3njwhAGVCuBAAC4hoAAt0EqVQXmdKVLGbGmzgE",
    "LOSS": "CAACAgUAAxkBAAEQTytpcz9VQoHyZ5ClbKSqKCJbpqX6yQACahYAAl1wAAFUL9xOdyh8UL84BA",
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
# PREDICTION ENGINE (YOUR EXACT LOGIC)
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
        return max(50, base - (streak_loss * 6))

    def get_pattern_signal(self, current_streak_loss):
        if len(self.history) < 10:
            return random.choice(["BIG", "SMALL"])

        h = self.history
        last = h[0]
        prev1 = h[1]
        prev2 = h[2]

        prediction = None

        # PHASE 1
        is_zigzag = (last != prev1 and prev1 != prev2)
        is_dragon = (last == prev1 and prev1 == prev2)
        is_aabb = (last == prev1 and prev2 == h[3] and last != prev2)

        # PHASE 2
        if is_dragon:
            prediction = last
        elif is_zigzag:
            prediction = "SMALL" if last == "BIG" else "BIG"
        elif is_aabb:
            prediction = "SMALL" if last == "BIG" else "BIG"
        else:
            last_6 = h[:6]
            if last_6.count("BIG") > last_6.count("SMALL"):
                prediction = "BIG"
            else:
                prediction = "SMALL"

        # PHASE 3
        if 1 <= current_streak_loss <= 3:
            prediction = "SMALL" if prediction == "BIG" else "BIG"

        if current_streak_loss >= 4:
            prediction = last

        self.last_prediction = prediction
        return prediction


# =========================
# STATE
# =========================
def now_bd_str() -> str:
    return datetime.now(BD_TZ).strftime("%I:%M:%S %p").lstrip("0")


def calc_current_1m_period(now: datetime) -> str:
    date_str = now.strftime("%Y%m%d")
    total_slots = (now.hour * 60) + now.minute + 1
    return f"{date_str}01{total_slots:04d}"


@dataclass
class ActiveBet:
    predicted_issue: str
    pick: str
    checking_msg_ids: Dict[int, int] = field(default_factory=dict)
    timer_tasks: Dict[int, asyncio.Task] = field(default_factory=dict)


@dataclass
class BotState:
    running: bool = False
    session_id: int = 0
    engine: PredictionEngine = field(default_factory=PredictionEngine)
    active: Optional[ActiveBet] = None
    last_signal_issue: Optional[str] = None

    wins: int = 0
    losses: int = 0
    streak_win: int = 0
    streak_loss: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

    unlocked: bool = False
    expected_password: str = PASSWORD_FALLBACK

    selected_targets: List[int] = field(default_factory=lambda: [TARGETS["MAIN_GROUP"]])

    auto_schedule_enabled: bool = True
    started_by_schedule: bool = False
    graceful_stop_requested: bool = False
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)


state = BotState()


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
# PREMIUM MESSAGE STYLE (UPGRADED)
# =========================
def pick_badge(pick: str) -> str:
    return "🟢 <b>BIG</b>" if pick == "BIG" else "🔴 <b>SMALL</b>"


def _hype_emoji_by_minutes(delta_mins: int) -> str:
    # more hype if longer wait
    if delta_mins >= 180:
        return "🔥🚀✨"
    if delta_mins >= 60:
        return "🔥✨"
    if delta_mins >= 30:
        return "✨⏳"
    return "⏳"


def review_next_block(now: datetime) -> str:
    next_time_str, delta_mins = _next_window_start(now)
    hype = _hype_emoji_by_minutes(delta_mins)

    return (
        f"⏺সিগন্যাল কেমন হলো? অবশ্যই এখানে রিভিউ দিবেন 💋\n\n"
        f"{OWNER_USERNAME}  ❤️\n\n"
        f"এবং পরবর্তী সিগন্যাল হবে <b>{next_time_str}</b> {hype}\n\n"
        f"{REG_LINK}\n\n"
        f"অ্যাকাউন্ট খুলে ইনবক্সে ইউআইডি দিন। এবং মিনিমাম 300 টাকা ডিপোজিট করে বট সিগন্যাল উপভোগ করুন এবং আনলিমিটেড হ্যাক নিন 🌟✅\n\n"
        f"{OWNER_USERNAME} ❤️"
    )


def format_signal(issue: str, pick: str, conf: int) -> str:
    now = datetime.now(BD_TZ)
    return (
        f"{BRAND_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎯 <b>ENTRY:</b> {pick_badge(pick)}\n"
        f"✨ <b>CONFIDENCE:</b> 🔥 <b>{conf}%</b>\n"
        f"🧠 <b>RECOVERY:</b> <b>{state.streak_loss}/{MAX_RECOVERY_STEPS}</b>\n"
        f"🕒 <b>TIME:</b> <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{review_next_block(now)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📣 <b>VIP:</b> <b><a href='{CHANNEL_LINK}'>JOIN NOW</a></b>"
    )


def format_checking(issue: str, clock: str) -> str:
    return (
        f"{clock} <b>RESULT CHECKING...</b>\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🕒 <b>{now_bd_str()}</b>"
    )


def format_result(issue: str, res_num: str, res_type: str, pick: str, is_win: bool) -> str:
    head = "✅ <b>WIN CONFIRMED</b>" if is_win else "❌ <b>LOSS CONFIRMED</b>"
    res_emoji = "🟢" if res_type == "BIG" else "🔴"
    return (
        f"{head}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎰 <b>RESULT:</b> {res_emoji} <b>{res_num} ({res_type})</b>\n"
        f"🎯 <b>YOUR PICK:</b> {pick_badge(pick)}\n"
        f"📊 <b>W:</b> <b>{state.wins}</b>  |  <b>L:</b> <b>{state.losses}</b>\n"
        f"🕒 <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📣 <b>VIP:</b> <b><a href='{CHANNEL_LINK}'>JOIN NOW</a></b>"
    )


def format_summary() -> str:
    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0
    return (
        "🛑 <b>SESSION SUMMARY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>TOTAL:</b> <b>{total}</b>\n"
        f"✅ <b>WIN:</b> <b>{state.wins}</b>\n"
        f"❌ <b>LOSS:</b> <b>{state.losses}</b>\n"
        f"🎯 <b>WIN RATE:</b> <b>{wr:.1f}%</b>\n"
        f"🔥 <b>MAX WIN STREAK:</b> <b>{state.max_win_streak}</b>\n"
        f"🧊 <b>MAX LOSS STREAK:</b> <b>{state.max_loss_streak}</b>\n"
        f"🕒 <b>CLOSED:</b> <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📣 <b>VIP:</b> <b><a href='{CHANNEL_LINK}'>JOIN NOW</a></b>\n"
        f"👤 <b>OWNER:</b> {OWNER_USERNAME}"
    )


# =========================
# PANEL
# =========================
def _chat_name(chat_id: int) -> str:
    if chat_id == TARGETS["MAIN_GROUP"]:
        return "MAIN GROUP"
    if chat_id == TARGETS["VIP"]:
        return "VIP"
    if chat_id == TARGETS["PUBLIC"]:
        return "PUBLIC"
    return str(chat_id)


def _windows_12h() -> str:
    out = []
    for a, b in AUTO_WINDOWS:
        a_m = _hhmm_to_minutes(a)
        b_m = _hhmm_to_minutes(b)
        out.append(f"{_minutes_to_12h_str(a_m)}-{_minutes_to_12h_str(b_m)}")
    return " | ".join(out)


def panel_text() -> str:
    running = "🟢 RUNNING" if state.running else "🔴 STOPPED"
    sel = state.selected_targets[:] if state.selected_targets else [TARGETS["MAIN_GROUP"]]
    sel_lines = "\n".join([f"✅ <b>{_chat_name(cid)}</b> <code>{cid}</code>" for cid in sel])

    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0

    auto = "⏰ <b>Auto Schedule:</b> ON" if state.auto_schedule_enabled else "⏰ <b>Auto Schedule:</b> OFF"
    origin = "🧩 <b>Session:</b> AUTO" if (state.running and state.started_by_schedule) else "🧩 <b>Session:</b> MANUAL"

    return (
        "🔐 <b>CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Status:</b> {running}\n"
        f"{origin}\n"
        f"{auto}\n"
        f"🗓 <b>Schedule:</b> <i>{_windows_12h()}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎯 <b>Send Signals To</b>\n"
        f"{sel_lines}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Stats:</b> ✅ <b>{state.wins}</b> | ❌ <b>{state.losses}</b> | 🎯 <b>{wr:.1f}%</b>\n"
        f"🔥 <b>Streak:</b> W <b>{state.streak_win}</b> | L <b>{state.streak_loss}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>Select then Start</i>"
    )


def selector_markup() -> InlineKeyboardMarkup:
    def btn(name: str, chat_id: int) -> InlineKeyboardButton:
        on = "✅" if chat_id in state.selected_targets else "⬜"
        return InlineKeyboardButton(f"{on} {name}", callback_data=f"TOGGLE:{chat_id}")

    rows = [
        [btn("MAIN GROUP", TARGETS["MAIN_GROUP"])],
        [btn("VIP", TARGETS["VIP"]), btn("PUBLIC", TARGETS["PUBLIC"])],
        [InlineKeyboardButton("⏰ Auto: ON" if state.auto_schedule_enabled else "⏰ Auto: OFF", callback_data="TOGGLE_AUTO")],
        [InlineKeyboardButton("⚡ Start 1 MIN", callback_data="START:1M")],
        [
            InlineKeyboardButton("🧠 Stop After Win", callback_data="STOP:GRACEFUL"),
            InlineKeyboardButton("🛑 Stop Now", callback_data="STOP:FORCE"),
        ],
        [InlineKeyboardButton("🔄 Refresh Panel", callback_data="REFRESH_PANEL")],
    ]
    return InlineKeyboardMarkup(rows)


# =========================
# HELPERS
# =========================
async def safe_delete(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass


async def broadcast_sticker(bot, sticker_id: str):
    for cid in state.selected_targets:
        try:
            await bot.send_sticker(cid, sticker_id)
        except Exception:
            pass


async def broadcast_message(bot, text: str) -> Dict[int, int]:
    out = {}
    for cid in state.selected_targets:
        try:
            m = await bot.send_message(
                cid,
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            out[cid] = m.message_id
        except Exception:
            pass
    return out


# =========================
# CHECKING TIMER (ROTATING CLOCK)
# =========================
CLOCK_FRAMES = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]


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
                    text=format_checking(issue, clock),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                break
            await asyncio.sleep(2.0)
    except asyncio.CancelledError:
        return


# =========================
# SESSION CONTROL
# =========================
def reset_stats():
    state.wins = 0
    state.losses = 0
    state.streak_win = 0
    state.streak_loss = 0
    state.max_win_streak = 0
    state.max_loss_streak = 0


async def stop_session(bot, reason: str = "manual"):
    state.session_id += 1
    state.running = False
    state.stop_event.set()

    # cancel timers + delete checking
    if state.active:
        for _cid, task in (state.active.timer_tasks or {}).items():
            try:
                task.cancel()
            except Exception:
                pass
        for cid, mid in (state.active.checking_msg_ids or {}).items():
            await safe_delete(bot, cid, mid)

    # Summary
    for cid in state.selected_targets:
        try:
            await bot.send_message(cid, format_summary(), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Exception:
            pass

    # Session close sticker (you provided)
    await broadcast_sticker(bot, STICKERS["SESSION_CLOSE"])

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

    # Session start sticker (you provided)
    await broadcast_sticker(bot, STICKERS["SESSION_START"])


# =========================
# ENGINE LOOP
# =========================
async def engine_loop(app: Application, my_session: int):
    bot = app.bot

    while state.running and state.session_id == my_session:
        if state.stop_event.is_set():
            break

        now = datetime.now(BD_TZ)
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
                for _cid, task in (state.active.timer_tasks or {}).items():
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
                else:
                    state.losses += 1
                    state.streak_loss += 1
                    state.streak_win = 0
                    state.max_loss_streak = max(state.max_loss_streak, state.streak_loss)
                    await broadcast_sticker(bot, STICKERS["LOSS"])

                await broadcast_message(bot, format_result(latest_issue, latest_num, latest_type, pick, is_win))

                state.active = None
                resolved_this_tick = True

                if state.graceful_stop_requested and is_win:
                    await stop_session(bot, reason="graceful_done")
                    break

        # 2) SIGNAL GENERATION
        if (not state.active) and is_safe_time and (not resolved_this_tick):
            if state.last_signal_issue != current_period:
                if state.streak_loss >= MAX_RECOVERY_STEPS:
                    await broadcast_message(bot, "🧊 <b>SAFETY STOP</b>\n<i>Recovery limit reached.</i>")
                    await stop_session(bot, reason="max_steps")
                    break

                pred = state.engine.get_pattern_signal(state.streak_loss)
                conf = state.engine.calc_confidence(state.streak_loss)

                # send your fixed sticker set
                await broadcast_sticker(bot, STICKERS["PRED_BIG"] if pred == "BIG" else STICKERS["PRED_SMALL"])
                await broadcast_message(bot, format_signal(current_period, pred, conf))

                # checking message + timer
                checking_ids = {}
                timer_tasks = {}
                for cid in state.selected_targets:
                    try:
                        m = await bot.send_message(cid, format_checking(current_period, "🕛"), parse_mode=ParseMode.HTML)
                        checking_ids[cid] = m.message_id
                        timer_tasks[cid] = asyncio.create_task(run_checking_timer(bot, cid, m.message_id, current_period))
                    except Exception:
                        pass

                state.active = ActiveBet(
                    predicted_issue=current_period,
                    pick=pred,
                    checking_msg_ids=checking_ids,
                    timer_tasks=timer_tasks,
                )
                state.last_signal_issue = current_period

        await asyncio.sleep(0.6)


# =========================
# AUTO SCHEDULER LOOP
# =========================
async def scheduler_loop(app: Application):
    while True:
        try:
            now = datetime.now(BD_TZ)
            in_window = is_now_in_any_window(now)

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
# COMMANDS & CALLBACKS
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.expected_password = await get_live_password()
    state.unlocked = False
    await update.message.reply_text("🔒 <b>SYSTEM LOCKED</b>\n✅ Password দিন:", parse_mode=ParseMode.HTML)


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.unlocked:
        state.expected_password = await get_live_password()
        await update.message.reply_text("🔒 <b>LOCKED</b>", parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if not state.unlocked:
        state.expected_password = await get_live_password()
        if txt == state.expected_password:
            state.unlocked = True
            await update.message.reply_text("✅ <b>UNLOCKED</b>", parse_mode=ParseMode.HTML)
            await update.message.reply_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        else:
            await update.message.reply_text("❌ <b>WRONG PASSWORD</b>", parse_mode=ParseMode.HTML)
        return


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    if not state.unlocked:
        await q.edit_message_text("🔒 <b>LOCKED</b>")
        return

    if data == "REFRESH_PANEL":
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        return

    if data.startswith("TOGGLE:"):
        cid = int(data.split(":")[1])
        if cid in state.selected_targets:
            state.selected_targets.remove(cid)
        else:
            state.selected_targets.append(cid)
        if not state.selected_targets:
            state.selected_targets = [TARGETS["MAIN_GROUP"]]
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        return

    if data == "TOGGLE_AUTO":
        state.auto_schedule_enabled = not state.auto_schedule_enabled
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        return

    if data == "START:1M":
        if state.running:
            await stop_session(context.bot, reason="restart_manual")
        await start_session(context.bot, started_by_schedule=False)
        context.application.create_task(engine_loop(context.application, state.session_id))
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        return

    if data == "STOP:FORCE":
        if state.running:
            await stop_session(context.bot, reason="force")
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
        return

    if data == "STOP:GRACEFUL":
        if state.running:
            state.graceful_stop_requested = True
            if state.streak_loss == 0 and state.active is None:
                await stop_session(context.bot, reason="graceful_now")
        await q.edit_message_text(panel_text(), parse_mode=ParseMode.HTML, reply_markup=selector_markup())
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
