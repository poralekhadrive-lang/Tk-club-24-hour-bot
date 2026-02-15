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
from telegram.error import RetryAfter, TimedOut, NetworkError

# =========================
# CONFIG
# =========================
# ⚠️ SECURITY: Never hardcode token in public.
# Set env: BOT_TOKEN="xxxx" then run.
BOT_TOKEN = os.environ.get("8456002611:AAHsSlu_bv1iVqKuTLjIb0BNvUpxJiBo1p8", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var not set. Set BOT_TOKEN and restart.")

OWNER_USERNAME = "@OWNER_MARUF_TOP"
OWNER_LINK = "https://t.me/OWNER_MARUF_TOP"

CHANNEL_LINK = "https://t.me/Vip_signal_group_11"
REG_LINK = "https://tkclub2.com/#/register?invitationCode=42584207677"

STEP_LINK = "https://brand-trx-step-maker.netlify.app/"
STEP_LINE = f"🔗 <a href='{STEP_LINK}'>8 Step Link</a> — <b>ক্লিক করে 8 step maintain করুন</b> ✅"

API_URL = "https://api880.inpay88.net/api/webapi/GetNoaverageEmerdList"
BD_TZ = timezone(timedelta(hours=6))

FETCH_TIMEOUT = 6.0
MAX_RECOVERY_STEPS = 8

TARGETS = {
    "MAIN": -1003263928753,
    "VIP": -1002892329434,
    "PUBLIC": -1003034758076,
}

# =========================
# STICKERS
# =========================
STICKERS = {
    "SESSION_START": "CAACAgUAAxkBAAEQYyFpfc4wbxDAkFww3cpExFCaz1iDbQACoB0AAhxruVZktiP7rGZdATgE",
    "SESSION_CLOSE": "CAACAgUAAxkBAAEQYyJpfc4wO83n6lkaDSMVxxFDzq6erwACaB4AAkbvuFbNxjX-zft8RzgE",
    "PRED_BIG": "CAACAgUAAxkBAAEQYx5pfc4AATgOO5wT5AABMN-bMJl5k_RQAALhHQACDsygVwoi0Z3WbYKyOAQ",
    "PRED_SMALL": "CAACAgUAAxkBAAEQYx1pfc4AAYYby230GOERm9UbVwrbZrcAAl8ZAAKDVphXk0mOoe8u1Zc4BA",
    "WIN": [
        "CAACAgUAAxkBAAEQTzNpcz9ns8rx_5xmxk4HHQOJY2uUQQAC3RoAAuCpcFbMKj0VkxPOdTgE",
        "CAACAgUAAxkBAAEQTzRpcz9ni_I4CjwFZ3iSt4xiXxFgkwACkxgAAnQKcVYHd8IiRqfBXTgE",
        "CAACAgUAAxkBAAEQTx9pcz8GryuxGBMFtzRNRbiCTg9M8wAC5xYAAkN_QFWgd5zOh81JGDgE",
    ],
    "LOSS": "CAACAgUAAxkBAAEQTytpcz9VQoHyZ5ClbKSqKCJbpqX6yQACahYAAl1wAAFUL9xOdyh8UL84BA",
    "SUPER_WIN": {
        2: "CAACAgUAAxkBAAEQTiBpcmUfm9aQmlIHtPKiG2nE2e6EeAACcRMAAiLWqFSpdxWmKJ1TXzgE",
        3: "CAACAgUAAxkBAAEQTiFpcmUgdgJQ_czeoFyRhNZiZI2lwwAC8BcAAv8UqFSVBQEdUW48HTgE",
        4: "CAACAgUAAxkBAAEQTiJpcmUgSydN-tKxoSVdFuAvCcJ3fQACvSEAApMRqFQoUYBnH5Pc7TgE",
        5: "CAACAgUAAxkBAAEQTiNpcmUgu_dP3wKT2k94EJCiw3u52QACihoAArkfqFSlrldtXbLGGDgE",
        6: "CAACAgUAAxkBAAEQTiRpcmUhQJUjd2ukdtfEtBjwtMH4MAACWRgAAsTFqVTato0SmSN-6jgE",
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
# UTILS (CLEAN)
# =========================
def now_bd() -> datetime:
    return datetime.now(BD_TZ)


def now_bd_str() -> str:
    return now_bd().strftime("%I:%M:%S %p")


def fmt_owner() -> str:
    return f"<a href='{OWNER_LINK}'>{OWNER_USERNAME}</a>"


def footer_line() -> str:
    return (
        f"{STEP_LINE}\n"
        f"📣 <a href='{CHANNEL_LINK}'>VIP Channel</a>  |  🧾 <a href='{REG_LINK}'>Open Account</a>  |  👤 {fmt_owner()}"
    )


def fancy_bs(t: str) -> str:
    t = (t or "").upper()
    if t == "BIG":
        return "🇧 🇮 🇬"
    if t == "SMALL":
        return "🇸 🇲 🇦 🇱 🇱"
    return t


def badge(pick: str) -> str:
    return "🟢 <b>🇧 🇮 🇬</b>" if pick == "BIG" else "🔴 <b>🇸 🇲 🇦 🇱 🇱</b>"


def result_emoji(res_type: str) -> str:
    return "🟢" if res_type == "BIG" else "🔴"


CLOCK_SPIN = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]

# =========================
# ✅ STICKER PRIORITY QUEUE
# =========================
_chat_locks: Dict[int, asyncio.Lock] = {}


def _lock_for(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


async def send_sticker_priority(bot, chat_id: int, sticker_id: str, tries: int = 7) -> bool:
    if not sticker_id:
        return False

    lock = _lock_for(chat_id)
    async with lock:
        for attempt in range(tries):
            try:
                await bot.send_sticker(chat_id, sticker_id)
                await asyncio.sleep(0.70)  # throttle per chat
                return True
            except RetryAfter as e:
                wait_s = float(getattr(e, "retry_after", 2.0))
                await asyncio.sleep(wait_s + 0.6)
            except (TimedOut, NetworkError):
                await asyncio.sleep(0.9 + attempt * 0.25)
            except Exception:
                await asyncio.sleep(0.8 + attempt * 0.2)
        return False


async def send_sticker_sequence(bot, chat_id: int, stickers: List[str]) -> None:
    for s in stickers:
        await send_sticker_priority(bot, chat_id, s)


# =========================
# ✅ PREDICTION ENGINE (YOUR PROVIDED LOGIC - HUBUHU)
# =========================
class PredictionEngine:
    def __init__(self):
        self.history: List[str] = []  # ['BIG', 'SMALL', ...]
        self.raw_history: List[int] = []  # [7, 2, 9, ...]
        self.zigzag_threshold = 3
        self.last_period = None

        # UI hints
        self.last_pattern: str = "NORMAL"
        self.zigzag_mode: bool = False

    def update_history(self, issue_data: dict):
        try:
            num = int(issue_data["number"])
            res_type = "BIG" if num >= 5 else "SMALL"

            # ডুপ্লিকেট ডাটা এড়ানোর জন্য পিরিয়ড চেক
            if (self.last_period is None) or (self.last_period != issue_data.get("issueNumber")):
                self.history.insert(0, res_type)
                self.raw_history.insert(0, num)
                self.last_period = issue_data.get("issueNumber")

                # মেমোরি ক্লিনআপ (সর্বশেষ ১০০ ডাটা রাখবে)
                self.history = self.history[:100]
                self.raw_history = self.raw_history[:100]
        except Exception:
            pass

    def _detect_pattern(self) -> str:
        if len(self.history) < 5:
            return "NORMAL"

        # ১. ড্রাগন ট্রেন্ড ডিটেকশন (একই রেজাল্ট ৪ বারের বেশি)
        if all(x == self.history[0] for x in self.history[:4]):
            return "DRAGON"

        # ২. জিকজ্যাক মুড ডিটেকশন (B-S-B-S)
        zigzag_count = 0
        for i in range(len(self.history) - 1):
            if self.history[i] != self.history[i + 1]:
                zigzag_count += 1
            else:
                break
        if zigzag_count >= self.zigzag_threshold:
            return "ZIGZAG"

        return "NORMAL"

    def get_pattern_signal(self, streak_loss: int) -> str:
        if not self.history:
            self.last_pattern = "NORMAL"
            self.zigzag_mode = False
            return "BIG"

        last_res = self.history[0]
        pattern = self._detect_pattern()

        # লজিক ১: যদি ড্রাগন ট্রেন্ড থাকে (টানা ৪ বার বিগ/স্মল)
        if pattern == "DRAGON":
            # ট্রেন্ডের সাথে থাকাই বুদ্ধিমানের কাজ
            prediction = last_res

        # লজিক ২: যদি জিকজ্যাক মুড থাকে (B-S-B-S)
        elif pattern == "ZIGZAG":
            # জিকজ্যাক মুড ভাঙ্গার সম্ভাবনা কম থাকলে উল্টোটা দিন
            prediction = "SMALL" if last_res == "BIG" else "BIG"

        # লজিক ৩: যখন মার্কেট ট্র্যাপ করে (টানা লস হচ্ছে)
        elif streak_loss >= 2:
            # ট্র্যাপ থেকে বাঁচতে লাস্ট রেজাল্টের উল্টোটা দিয়ে রিস্ক নিন
            prediction = "SMALL" if last_res == "BIG" else "BIG"

        # লজিক ৪: নরমাল মার্কেট (বেস্ট ম্যাথমেটিক্যাল এভারেজ)
        else:
            prediction = last_res  # ট্রেন্ড ফলো করা ভালো

        self.last_pattern = pattern
        self.zigzag_mode = (pattern == "ZIGZAG")
        return prediction

    def calc_confidence(self, streak_loss: int) -> int:
        # লস বাড়লে কনফিডেন্স কমান যাতে ইউজাররা কম টাকা লাগায়
        conf = random.randint(93, 97)
        return max(45, conf - (streak_loss * 8))


# =========================
# API FETCH (return list)
# =========================
def _fetch_latest_list_sync() -> List[dict]:
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
            lst = (((data or {}).get("data") or {}).get("list") or [])
            return [x for x in lst if isinstance(x, dict)]
    except Exception as e:
        print("API Error:", e)
    return []


async def fetch_latest_list() -> List[dict]:
    return await asyncio.to_thread(_fetch_latest_list_sync)


# =========================
# TIME PRESETS
# =========================
SCHEDULE_PRESETS = [
    ("NIGHT_09", "🕘 রাত: 09:00 PM ➜ 09:30 PM", "09:00PM-09:30PM"),
    ("NIGHT_11", "🕚 রাত: 11:00 PM ➜ 11:30 PM", "11:00PM-11:30PM"),
    ("MORNING_10", "🕙 সকাল: 10:00 AM ➜ 10:30 AM", "10:00AM-10:30AM"),
    ("NOON_12", "🕛 দুপুর: 12:00 PM ➜ 12:30 PM", "12:00PM-12:30PM"),
    ("EVE_03", "🕒 বিকাল: 03:00 PM ➜ 03:30 PM", "03:00PM-03:30PM"),
    ("EVE_07", "🕖 সন্ধ্যা: 07:00 PM ➜ 07:30 PM", "07:00PM-07:30PM"),
]


def parse_time_window(txt: str) -> Optional[Tuple[int, int]]:
    try:
        raw = txt.strip().upper().replace(" ", "")
        a, b = raw.split("-")

        def to_min(t):
            ampm = t[-2:]
            hm = t[:-2]
            hh, mm = hm.split(":")
            hh = int(hh)
            mm = int(mm)
            if ampm == "AM":
                if hh == 12:
                    hh = 0
            else:
                if hh != 12:
                    hh += 12
            return hh * 60 + mm

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


# =========================
# DATA CLASSES
# =========================
@dataclass
class ChannelConfig:
    key: str
    chat_id: int
    name: str
    window_text: str = "Not Set"
    window_min: Optional[Tuple[int, int]] = None
    win_target: int = 0


@dataclass
class ActiveBet:
    predicted_issue: str
    pick: str
    pred_msg_id: Optional[int] = None
    checking_msg_id: Optional[int] = None
    checking_task: Optional[asyncio.Task] = None


@dataclass
class BotState:
    unlocked: bool = False
    expected_password: str = "2222"

    admin_chat_id: Optional[int] = None
    panel_message_id: Optional[int] = None
    menu_mode: str = "CHOOSE_CHANNEL"

    waiting_for: Optional[str] = None
    waiting_channel_key: Optional[str] = None

    channels: Dict[str, ChannelConfig] = field(default_factory=dict)
    current_channel_key: Optional[str] = None

    schedule_mode: bool = True

    running: bool = False
    session_id: int = 0
    started_by_schedule: bool = False
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    graceful_stop_requested: bool = False

    engine: PredictionEngine = field(default_factory=PredictionEngine)
    active: Optional[ActiveBet] = None

    wins: int = 0
    losses: int = 0
    streak_win: int = 0
    streak_loss: int = 0


state = BotState()


def init_channels():
    state.channels = {
        "MAIN": ChannelConfig("MAIN", TARGETS["MAIN"], "MAIN GROUP"),
        "VIP": ChannelConfig("VIP", TARGETS["VIP"], "VIP"),
        "PUBLIC": ChannelConfig("PUBLIC", TARGETS["PUBLIC"], "PUBLIC"),
    }


# =========================
# CLEAN MESSAGE TEMPLATES
# =========================
def msg_signal(issue: str, pick: str, conf: int, streak_loss: int, zigzag: bool) -> str:
    # UI: zigzag true হলে zigzag, নাহলে normal
    mode = "⚡ <b>ZIGZAG</b>" if zigzag else "✅ <b>NORMAL</b>"
    return (
        f"🔥 <b>VIP SIGNAL</b>\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"{mode}\n"
        f"🎯 <b>PICK:</b> {badge(pick)}\n"
        f"✨ <b>CONF:</b> <b>{conf}%</b>  |  🧠 <b>REC:</b> <b>{streak_loss}/{MAX_RECOVERY_STEPS}</b>\n"
        f"⏱ <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{footer_line()}"
    )


def msg_checking(issue: str, spin: str, dots: str) -> str:
    return (
        f"{spin} <b>RESULT CHECKING{dots}</b>\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"⏱ <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{footer_line()}"
    )


def msg_result(issue: str, res_num: str, res_type: str, pick: str, wins: int, losses: int, is_win: bool) -> str:
    head = "✅ <b>WIN</b>" if is_win else "❌ <b>LOSS</b>"
    return (
        f"{head}\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
        f"🎰 <b>RESULT:</b> {result_emoji(res_type)} <b>{res_num} ({fancy_bs(res_type)})</b>\n"
        f"🎯 <b>PICK:</b> {badge(pick)}\n"
        f"📊 ✅ <b>{wins}</b> | ❌ <b>{losses}</b>\n"
        f"⏱ <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{footer_line()}"
    )


def msg_session_close(cfg: ChannelConfig, wins: int, losses: int) -> str:
    total = wins + losses
    wr = (wins / total * 100) if total else 0.0
    nxt = "<i>Not scheduled</i>"
    if cfg.window_min:
        a, b = cfg.window_min
        nxt = f"<b>{minutes_to_ampm(a)} - {minutes_to_ampm(b)}</b>"
    return (
        f"🛑 <b>SESSION STOP</b>\n"
        f"📦 <b>Total:</b> <b>{total}</b>  |  ✅ <b>W:</b> <b>{wins}</b>  |  ❌ <b>L:</b> <b>{losses}</b>  |  🎯 <b>{wr:.1f}%</b>\n"
        f"⏭️ <b>Next:</b> {nxt}\n"
        f"⏱ <b>{now_bd_str()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{footer_line()}"
    )


# =========================
# SEND HELPERS
# =========================
async def send_sticker(bot, chat_id: int, sticker_id: str):
    await send_sticker_priority(bot, chat_id, sticker_id)


async def send_html(bot, chat_id: int, text: str) -> Optional[int]:
    try:
        m = await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        return m.message_id
    except Exception:
        return None


async def edit_html(bot, chat_id: int, msg_id: int, text: str):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def delete_msg(bot, chat_id: int, msg_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except Exception:
        pass


def pred_sticker_for(pick: str) -> str:
    return STICKERS["PRED_BIG"] if pick == "BIG" else STICKERS["PRED_SMALL"]


# =========================
# PANEL UI
# =========================
def choose_channel_text() -> str:
    return "📌 <b>CHOOSE CHANNEL</b>\nকোন গ্রুপে চালাবেন সিলেক্ট করুন ✅"


def choose_channel_markup() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("✅ MAIN GROUP", callback_data="OPEN:MAIN")],
        [InlineKeyboardButton("✅ VIP", callback_data="OPEN:VIP"),
         InlineKeyboardButton("✅ PUBLIC", callback_data="OPEN:PUBLIC")],
    ]
    return InlineKeyboardMarkup(rows)


def preset_time_text() -> str:
    lines = ["🕘 <b>SELECT TIME</b>"]
    for _, label, _ in SCHEDULE_PRESETS:
        lines.append(label)
    return "\n".join(lines)


def preset_time_markup() -> InlineKeyboardMarkup:
    rows = []
    for code, label, _raw in SCHEDULE_PRESETS:
        rows.append([InlineKeyboardButton(label, callback_data=f"TIME:{code}")])
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="TIME_BACK")])
    return InlineKeyboardMarkup(rows)


def control_panel_text(cfg: ChannelConfig) -> str:
    status = "🟢 RUNNING" if state.running else "🔴 STOPPED"
    sch = "✅ ON" if state.schedule_mode else "❌ OFF"
    tw = f"<b>{cfg.window_text}</b>" if cfg.window_min else "<i>Not Set</i>"
    wt = f"<b>{cfg.win_target}</b>" if cfg.win_target > 0 else "<i>Not Set</i>"
    total = state.wins + state.losses
    wr = (state.wins / total * 100) if total else 0.0
    return (
        f"🎛 <b>{cfg.name} PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Status: {status}\n"
        f"⏰ Schedule: <b>{sch}</b>\n"
        f"🕘 Time: {tw}\n"
        f"🏆 Win: {wt}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 ✅ <b>{state.wins}</b> | ❌ <b>{state.losses}</b> | 🎯 <b>{wr:.1f}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {fmt_owner()}"
    )


def control_panel_markup() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("⏰ Schedule ON/OFF", callback_data="TOGGLE_SCHEDULE")],
        [InlineKeyboardButton("🕘 Select Time", callback_data="SET_TIME"),
         InlineKeyboardButton("🏆 Select Win", callback_data="SET_WIN")],
        [InlineKeyboardButton("⚡ Start 1 MIN", callback_data="START")],
        [InlineKeyboardButton("🧠 Stop After Win", callback_data="STOP_GRACEFUL"),
         InlineKeyboardButton("🛑 Stop Now", callback_data="STOP_FORCE")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="REFRESH")],
        [InlineKeyboardButton("⬅️ Back", callback_data="BACK")],
    ]
    return InlineKeyboardMarkup(rows)


async def render_panel(bot):
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

        if state.menu_mode == "TIME_PRESET":
            await bot.edit_message_text(
                chat_id=state.admin_chat_id,
                message_id=state.panel_message_id,
                text=preset_time_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=preset_time_markup(),
                disable_web_page_preview=True,
            )
            return

        cfg = state.channels.get(state.current_channel_key or "MAIN")
        await bot.edit_message_text(
            chat_id=state.admin_chat_id,
            message_id=state.panel_message_id,
            text=control_panel_text(cfg),
            parse_mode=ParseMode.HTML,
            reply_markup=control_panel_markup(),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def ensure_panel(bot, chat_id: int):
    state.admin_chat_id = chat_id

    if state.panel_message_id:
        try:
            await bot.delete_message(chat_id=state.admin_chat_id, message_id=state.panel_message_id)
        except Exception:
            pass
        state.panel_message_id = None

    m = await bot.send_message(chat_id, "✅ Panel Loading...", parse_mode=ParseMode.HTML)
    state.panel_message_id = m.message_id
    state.menu_mode = "CHOOSE_CHANNEL"
    await render_panel(bot)


# =========================
# SESSION CONTROL
# =========================
def reset_stats():
    state.wins = 0
    state.losses = 0
    state.streak_win = 0
    state.streak_loss = 0


async def start_session(app_: Application, started_by_schedule: bool):
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
    reset_stats()

    await send_sticker(app_.bot, cfg.chat_id, STICKERS["SESSION_START"])


async def stop_session(app_: Application, reason: str = "manual"):
    cfg = state.channels.get(state.current_channel_key or "MAIN")
    if not cfg:
        return

    state.session_id += 1
    state.running = False
    state.stop_event.set()

    if state.active:
        if state.active.checking_task:
            state.active.checking_task.cancel()
        if state.active.checking_msg_id:
            await delete_msg(app_.bot, cfg.chat_id, state.active.checking_msg_id)
        state.active = None

    await send_sticker(app_.bot, cfg.chat_id, STICKERS["SESSION_CLOSE"])
    await send_html(app_.bot, cfg.chat_id, msg_session_close(cfg, state.wins, state.losses))


# =========================
# CHECKING SPINNER
# =========================
async def checking_spinner_task(bot, chat_id: int, issue: str, msg_id: int, my_session: int):
    i = 0
    while state.running and state.session_id == my_session and state.active and state.active.predicted_issue == issue:
        spin = CLOCK_SPIN[i % len(CLOCK_SPIN)]
        dots = "." * ((i % 3) + 1)
        await edit_html(bot, chat_id, msg_id, msg_checking(issue, spin, dots))
        i += 1
        await asyncio.sleep(1.1)


# =========================
# ENGINE LOOP (Sequence fixed exactly as you asked)
# =========================
async def engine_loop(app_: Application, my_session: int):
    cfg = state.channels.get(state.current_channel_key or "MAIN")
    if not cfg:
        return

    bot = app_.bot
    chat_id = cfg.chat_id
    last_predicted_issue_sent: Optional[str] = None

    while state.running and state.session_id == my_session:
        if state.stop_event.is_set():
            break

        items = await fetch_latest_list()
        if not items:
            await asyncio.sleep(0.7)
            continue

        latest_data = items[0]
        state.engine.update_history(latest_data)

        latest_issue = str(latest_data.get("issueNumber"))
        latest_num = str(latest_data.get("number"))

        # A) RESULT FEEDBACK: when active issue appears inside last 10 list
        if state.active:
            want_issue = str(state.active.predicted_issue)

            matched = None
            for it in items:
                if str(it.get("issueNumber")) == want_issue:
                    matched = it
                    break

            if matched:
                # --- stop spinner task first ---
                if state.active.checking_task:
                    state.active.checking_task.cancel()

                # --- DELETE checking message BEFORE feedback (as per your flow) ---
                if state.active.checking_msg_id:
                    await delete_msg(bot, chat_id, state.active.checking_msg_id)

                res_num = str(matched.get("number"))
                res_type = "BIG" if int(res_num) >= 5 else "SMALL"
                pick = state.active.pick
                is_win = (pick == res_type)

                # --- WIN/LOSS sticker (priority) ---
                if is_win:
                    state.wins += 1
                    state.streak_win += 1
                    state.streak_loss = 0

                    if state.streak_win in STICKERS["SUPER_WIN"]:
                        await send_sticker(bot, chat_id, STICKERS["SUPER_WIN"][state.streak_win])
                    else:
                        await send_sticker(bot, chat_id, random.choice(STICKERS["WIN"]))
                else:
                    state.losses += 1
                    state.streak_loss += 1
                    state.streak_win = 0
                    await send_sticker(bot, chat_id, STICKERS["LOSS"])

                # --- result message ---
                await send_html(
                    bot,
                    chat_id,
                    msg_result(want_issue, res_num, res_type, pick, state.wins, state.losses, is_win),
                )

                # clear active
                state.active = None

                # stops
                if cfg.win_target > 0 and state.wins >= cfg.win_target:
                    await stop_session(app_, reason="win_target")
                    break

                if state.graceful_stop_requested and is_win:
                    await stop_session(app_, reason="graceful_done")
                    break

        # B) SEND NEXT PREDICTION (once per next_issue)
        try:
            next_issue = str(int(latest_issue) + 1)
        except Exception:
            next_issue = None

        if (not state.active) and next_issue and (next_issue != last_predicted_issue_sent):
            if state.streak_loss >= MAX_RECOVERY_STEPS:
                await send_html(
                    bot,
                    chat_id,
                    f"🧯 <b>SAFETY STOP</b>\n<i>Recovery limit reached.</i>\n━━━━━━━━━━━━━━━━━━\n{footer_line()}",
                )
                await stop_session(app_, reason="max_steps")
                break

            pred = state.engine.get_pattern_signal(state.streak_loss)
            conf = state.engine.calc_confidence(state.streak_loss)

            # 1) Prediction sticker
            await send_sticker(bot, chat_id, pred_sticker_for(pred))

            # 2) Prediction message
            pred_msg_id = await send_html(
                bot,
                chat_id,
                msg_signal(next_issue, pred, conf, state.streak_loss, state.engine.zigzag_mode),
            )

            # 3) Checking message (animated)
            checking_id = await send_html(bot, chat_id, msg_checking(next_issue, "🕛", "."))

            state.active = ActiveBet(
                predicted_issue=next_issue,
                pick=pred,
                pred_msg_id=pred_msg_id,
                checking_msg_id=checking_id,
            )
            last_predicted_issue_sent = next_issue

            if checking_id:
                state.active.checking_task = asyncio.create_task(
                    checking_spinner_task(bot, chat_id, next_issue, checking_id, my_session)
                )

        await asyncio.sleep(0.7)


# =========================
# SCHEDULER LOOP
# =========================
def is_now_in_window(cfg: ChannelConfig, now: datetime) -> bool:
    if not cfg.window_min:
        return False
    a, b = cfg.window_min
    mins = now.hour * 60 + now.minute
    return a <= mins < b


async def scheduler_loop(app_: Application):
    while True:
        try:
            if not state.schedule_mode:
                await asyncio.sleep(2)
                continue

            if state.menu_mode != "CONTROL" or not state.current_channel_key:
                await asyncio.sleep(2)
                continue

            cfg = state.channels.get(state.current_channel_key)
            if not cfg:
                await asyncio.sleep(2)
                continue

            now = now_bd()
            in_window = is_now_in_window(cfg, now)

            if cfg.window_min:
                if in_window and (not state.running):
                    await start_session(app_, started_by_schedule=True)
                    app_.create_task(engine_loop(app_, state.session_id))
                elif (not in_window) and state.running and state.started_by_schedule:
                    await stop_session(app_, reason="schedule_end")

        except Exception as e:
            print("Scheduler error:", e)

        await asyncio.sleep(5)


# =========================
# COMMANDS + INPUT HANDLER
# =========================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state.unlocked = False
    state.waiting_for = "PASSWORD"
    state.menu_mode = "CHOOSE_CHANNEL"
    state.current_channel_key = None
    state.waiting_channel_key = None

    await update.message.reply_text("🔒 <b>SYSTEM LOCKED</b>\n✅ Password দিন:", parse_mode=ParseMode.HTML)


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not state.unlocked:
        await update.message.reply_text("🔒 <b>LOCKED</b>\n/start দিয়ে unlock করুন", parse_mode=ParseMode.HTML)
        return
    await ensure_panel(context.bot, update.effective_chat.id)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()

    if state.waiting_for == "PASSWORD" and not state.unlocked:
        if txt == state.expected_password:
            state.unlocked = True
            state.waiting_for = None
            await update.message.reply_text("✅ <b>UNLOCKED</b>", parse_mode=ParseMode.HTML)
            await ensure_panel(context.bot, update.effective_chat.id)
            return
        await update.message.reply_text("❌ <b>WRONG PASSWORD</b>", parse_mode=ParseMode.HTML)
        return

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


# =========================
# CALLBACKS
# =========================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = (q.data or "").strip()

    if q and q.message:
        state.admin_chat_id = q.message.chat_id
        state.panel_message_id = q.message.message_id

    try:
        await q.answer("✅", cache_time=0)
    except Exception:
        pass

    if not state.unlocked:
        return

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

    if data == "TOGGLE_SCHEDULE":
        state.schedule_mode = not state.schedule_mode
        if (not state.schedule_mode) and state.running and state.started_by_schedule:
            await stop_session(context.application, reason="schedule_toggled_off")
        await render_panel(context.bot)
        return

    if data == "SET_TIME":
        state.menu_mode = "TIME_PRESET"
        await render_panel(context.bot)
        return

    if data == "TIME_BACK":
        state.menu_mode = "CONTROL"
        await render_panel(context.bot)
        return

    if data.startswith("TIME:"):
        code = data.split(":")[1]
        raw = None
        for c, _label, r in SCHEDULE_PRESETS:
            if c == code:
                raw = r
                break
        tw = parse_time_window(raw) if raw else None
        if cfg and tw:
            cfg.window_min = tw
            cfg.window_text = raw
        state.menu_mode = "CONTROL"
        await render_panel(context.bot)
        return

    if data == "SET_WIN":
        state.waiting_for = "WIN"
        state.waiting_channel_key = cfg.key
        await context.bot.send_message(
            chat_id=state.admin_chat_id,
            text="🏆 <b>WIN TARGET</b>\nএই মেসেজে শুধু সংখ্যা লিখুন (Example: <code>40</code>)",
            parse_mode=ParseMode.HTML,
        )
        return

    if data == "START":
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
        await render_panel(context.bot)
        return


# =========================
# POST INIT
# =========================
async def post_init(app_: Application):
    app_.create_task(scheduler_loop(app_))


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
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
