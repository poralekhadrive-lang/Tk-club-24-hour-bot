import asyncio
import logging
import os
import random
import time
import json
import math
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
BOT_TOKEN = "8456002611:AAEvhsMJFXFuc0OYZCJhQ9WRKyUvryrfsso"  # <-- তোমার আসল টোকেন এখানে বসাও

OWNER_USERNAME = "@OWNER_MARUF_TOP"
OWNER_LINK = "https://t.me/OWNER_MARUF_TOP"

CHANNEL_LINK = "https://t.me/Vip_signal_group_11"
REG_LINK = "https://dkwin9.com/#/register?invitationCode=45555909939"

STEP_LINK = "https://brand-trx-step-maker.netlify.app/"
STEP_LINE = f"🔗 <a href='{STEP_LINK}'>8 Step Link</a> — <b>ক্লিক করে 8 step maintain করুন</b> ✅"

BD_TZ = timezone(timedelta(hours=6))

FETCH_TIMEOUT = 6.5
MAX_RECOVERY_STEPS = 8

TARGETS = {
    "MAIN": -1003263928753,
    "VIP": -1002892329434,
    "PUBLIC": -1003034758076,
}

# =========================
# ✅ TARGET API (WinGo 30 Seconds)
# =========================
TARGET_API_30S = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"

# ✅ PROXY GATES (same idea as your HTML)
PROXY_GATES = [
    ("CODETABS", "https://api.codetabs.com/v1/proxy?quest=", "ENC"),  # needs encode
    ("CORSPROXY", "https://corsproxy.io/?", "ENC"),                   # needs encode
    ("ALLORIGINS_RAW", "https://api.allorigins.win/raw?url=", "ENC"), # needs encode
    ("THINGPROXY", "https://thingproxy.freeboard.io/fetch/", "RAW"),  # append raw (no encode required, but safe)
    ("ALLORIGINS_GET", "https://api.allorigins.win/get?url=", "ENC"), # wrapper -> contents
]

_gate_index = 0  # rotates on failure

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
# UTILS
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

# =========================
# ✅ BIG/SMALL style (as you wanted)
# =========================
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

def pred_sticker_for(pick: str) -> str:
    return STICKERS["PRED_BIG"] if pick == "BIG" else STICKERS["PRED_SMALL"]

CLOCK_SPIN = ["🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚"]

# =========================
# ✅ YOUR HTML PREDICTION LOGIC (HUBUHU)
# hash = sin(seed*9999)*10000
# even => BIG else SMALL
# seed = nextPeriod % 100000
# =========================
def js_like_prediction(next_period: str) -> str:
    try:
        seed = int(int(next_period) % 100000)
    except Exception:
        # fallback
        seed = random.randint(1, 99999)

    h = math.sin(seed * 9999) * 10000
    is_big = (int(abs(h)) % 2) == 0
    return "BIG" if is_big else "SMALL"

# =========================
# ✅ API FETCH (30S via Proxy Rotation)
# returns latest issue dict: {issueNumber, number}
# =========================
def _safe_json_parse(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None

def _build_proxy_url(proxy_base: str, mode: str, url: str) -> str:
    # mode: "ENC" -> encode url; "RAW" -> append raw (but we still encode for safety)
    if mode == "RAW":
        # Thingproxy usually accepts raw URL directly
        return proxy_base + url
    # default: encode
    return proxy_base + requests.utils.quote(url, safe="")

def _fetch_latest_issue_sync_30s() -> Optional[dict]:
    global _gate_index

    ts = int(time.time() * 1000)
    api_with_params = f"{TARGET_API_30S}?pageNo=1&pageSize=5&t={ts}"

    # try all gates at most once per call
    for _ in range(len(PROXY_GATES)):
        name, proxy_base, mode = PROXY_GATES[_gate_index]
        final_url = _build_proxy_url(proxy_base, mode, api_with_params)

        try:
            r = requests.get(final_url, timeout=FETCH_TIMEOUT, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
            })
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")

            # Some proxies return wrapper JSON (allorigins/get) with "contents"
            raw_text = r.text.strip()
            data = _safe_json_parse(raw_text)

            if isinstance(data, dict) and "contents" in data:
                contents = data.get("contents")
                if isinstance(contents, str):
                    d2 = _safe_json_parse(contents)
                    data = d2 if d2 is not None else {"_contents": contents}

            # Some proxies return raw JSON string already
            if data is None:
                data = _safe_json_parse(raw_text)

            if not data:
                raise RuntimeError("No JSON data")

            # Expected: data.data.list[0] has issueNumber and number
            if isinstance(data, dict) and data.get("data") and data["data"].get("list"):
                latest = data["data"]["list"][0]
                if latest and "issueNumber" in latest and "number" in latest:
                    return latest

            raise RuntimeError("Invalid Data Structure")

        except Exception:
            # rotate gate
            _gate_index = (_gate_index + 1) % len(PROXY_GATES)
            continue

    return None

async def fetch_latest_issue_30s() -> Optional[dict]:
    return await asyncio.to_thread(_fetch_latest_issue_sync_30s)

# =========================
# TIME PRESETS (UNCHANGED)
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
# MESSAGE TEMPLATES
# =========================
def msg_signal(issue: str, pick: str, conf: int, streak_loss: int) -> str:
    return (
        f"🔥 <b>VIP SIGNAL</b>\n"
        f"🧾 <b>PERIOD:</b> <code>{issue}</code>\n"
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
    try:
        await bot.send_sticker(chat_id, sticker_id)
    except Exception:
        pass

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
        [InlineKeyboardButton("⚡ Start 30S", callback_data="START")],
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
        await asyncio.sleep(1.05)

# =========================
# ✅ ENGINE LOOP (30S API PERIOD + JS PRED LOGIC)
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

        latest_data = await fetch_latest_issue_30s()

        if latest_data:
            latest_issue = str(latest_data.get("issueNumber"))
            latest_num = str(latest_data.get("number"))

            try:
                latest_type = "BIG" if int(latest_num) >= 5 else "SMALL"
            except Exception:
                latest_type = "SMALL"

            # A) RESULT FEEDBACK when predicted issue arrives
            if state.active and state.active.predicted_issue == latest_issue:
                pick = state.active.pick
                is_win = (pick == latest_type)

                if state.active.checking_task:
                    state.active.checking_task.cancel()

                # delete checking first (must)
                if state.active.checking_msg_id:
                    await delete_msg(bot, chat_id, state.active.checking_msg_id)

                # win/loss sticker
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

                # feedback after sticker
                await send_html(
                    bot,
                    chat_id,
                    msg_result(latest_issue, latest_num, latest_type, pick, state.wins, state.losses, is_win),
                )

                state.active = None

                # stop by win target
                if cfg.win_target > 0 and state.wins >= cfg.win_target:
                    await stop_session(app_, reason="win_target")
                    break

                # graceful stop after win
                if state.graceful_stop_requested and is_win:
                    await stop_session(app_, reason="graceful_done")
                    break

            # B) SEND NEXT PREDICTION (period must be API-based)
            try:
                next_issue = str(int(latest_issue) + 1)
            except Exception:
                next_issue = None

            if (not state.active) and next_issue and (next_issue != last_predicted_issue_sent):
                if state.streak_loss >= MAX_RECOVERY_STEPS:
                    await send_html(bot, chat_id, f"🧯 <b>SAFETY STOP</b>\n<i>Recovery limit reached.</i>\n━━━━━━━━━━━━━━━━━━\n{footer_line()}")
                    await stop_session(app_, reason="max_steps")
                    break

                # ✅ prediction: HUBUHU your HTML logic
                pred = js_like_prediction(next_issue)

                # confidence (keep same style)
                conf = random.randint(94, 98)
                conf = max(55, conf - (state.streak_loss * 7))

                # 1) Prediction sticker
                await send_sticker(bot, chat_id, pred_sticker_for(pred))

                # 2) Prediction message
                pred_msg_id = await send_html(
                    bot,
                    chat_id,
                    msg_signal(next_issue, pred, conf, state.streak_loss),
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
