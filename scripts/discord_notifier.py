import os
import asyncio
import sqlite3
import pandas as pd
from datetime import datetime
import discord
from dotenv import load_dotenv
import ssl
import aiohttp
import pytz

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_PATH = os.getenv("DB_PATH")

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN missing in .env")
if not DB_PATH or not os.path.exists(DB_PATH):
    raise ValueError("❌ DB_PATH invalid or missing")

# ============================================================
# TIMEZONE
# ============================================================
IST = pytz.timezone("Asia/Kolkata")

# ============================================================
# SENT LOG
# ============================================================
SENT_LOG_PATH = "sent_discord_reminders.log"

def load_sent():
    if os.path.exists(SENT_LOG_PATH):
        with open(SENT_LOG_PATH) as f:
            return set(line.strip() for line in f)
    return set()

def save_sent(sent):
    with open(SENT_LOG_PATH, "w") as f:
        for k in sorted(sent):
            f.write(k + "\n")

sent_reminders = load_sent()

# ============================================================
# DISCORD BOT
# ============================================================
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# ============================================================
# DATABASE HELPERS
# ============================================================
def fetch_df(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_classes():
    return fetch_df("SELECT * FROM classes")

def get_assignments():
    return fetch_df("SELECT * FROM assignments")

# ============================================================
# CHANNEL RESOLVER
# ============================================================
async def get_channel_for_row(row):
    year = str(row.get("year", "")).strip()
    if "2025" not in year:
        return None

    course = str(row.get("course", "")).strip()
    batch = str(row.get("batch_name", "")).strip()
    mode = str(row.get("mode", "")).strip()

    key = "_".join([course, batch, year, mode]).upper().replace(" ", "_")
    env_key = f"DISCORD_{key}"

    channel_id = os.getenv(env_key)
    print("DEBUG CHANNEL KEY:", env_key, "→", channel_id)

    if not channel_id:
        print("❌ Missing ENV:", env_key)
        return None

    try:
        return await bot.fetch_channel(int(channel_id))
    except Exception as e:
        print("❌ Channel fetch failed:", e)
        return None

# ============================================================
# SEND MESSAGE
# ============================================================
async def send_message(channel, message):
    try:
        await channel.send(message)
        print(f"✅ Sent to #{channel.name}")
    except Exception as e:
        print("❌ Discord send error:", e)

# ============================================================
# REMINDER LOOP
# ============================================================
async def reminder_loop():
    await bot.wait_until_ready()
    print("🔁 Discord Reminder System Started")

    while not bot.is_closed():
        now = datetime.now(IST)

        # ================= CLASS REMINDERS =================
        for _, row in get_classes().iterrows():
            channel = await get_channel_for_row(row)
            if not channel:
                continue

            class_dt = pd.to_datetime(
                f"{row['date']} {row['time']}",
                errors="coerce"
            )
            if pd.isna(class_dt):
                continue

            # ✅ FIX: DB time is already IST (do NOT localize again)
            class_dt = class_dt.replace(tzinfo=IST)

            minutes_left = (class_dt - now).total_seconds() / 60

            reminders = [
                (45, 75, "60", "⏰ **Class Reminder (1 Hour Left)**"),
                (20, 40, "30", "⏰ **Class Reminder (30 Minutes Left)**"),
                (0, 5,  "2",  "🚀 **Class Starting Soon**"),
            ]

            for lo, hi, tag, title in reminders:
                if not (lo <= minutes_left <= hi):
                    continue

                key = f"class-{tag}-{row['session_name']}-{row['date']}-{channel.id}"
                if key in sent_reminders:
                    continue

                await send_message(
                    channel,
                    f"{title}\n\n"
                    f"📘 {row['session_name']}\n"
                    f"📚 {row['course']}\n"
                    f"👥 {row['batch_name']} {row['year']} ({row['mode']})\n"
                    f"🕒 Starts at {row['time']}"
                )
                sent_reminders.add(key)

        # ================= ASSIGNMENT REMINDERS =================
        for _, row in get_assignments().iterrows():
            channel = await get_channel_for_row(row)
            if not channel:
                continue

            due_dt = pd.to_datetime(row["due_date"], errors="coerce")
            if pd.isna(due_dt):
                continue

            # ✅ SAME FIX HERE
            due_dt = due_dt.replace(tzinfo=IST)

            minutes_left = (due_dt - now).total_seconds() / 60

            for m in (60, 30, 15):
                if not (m - 10 <= minutes_left <= m + 10):
                    continue

                key = f"assign-{row['subject']}-{row['due_date']}-{m}-{channel.id}"
                if key in sent_reminders:
                    continue

                await send_message(
                    channel,
                    f"📝 **Assignment Reminder**\n\n"
                    f"📌 {row['subject']}\n"
                    f"📚 {row['course']}\n"
                    f"👥 {row['batch_name']} {row['year']} ({row['mode']})\n"
                    f"⏳ {m} minutes remaining"
                )
                sent_reminders.add(key)

        save_sent(sent_reminders)
        await asyncio.sleep(15)

# ============================================================
# SSL PATCH
# ============================================================
original_init = aiohttp.ClientSession.__init__
def patched_init(self, *args, **kwargs):
    if "connector" not in kwargs:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs["connector"] = aiohttp.TCPConnector(ssl=ctx)
    return original_init(self, *args, **kwargs)

aiohttp.ClientSession.__init__ = patched_init

# ============================================================
# RUN
# ============================================================
@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")

async def main():
    async with bot:
        asyncio.create_task(reminder_loop())
        await bot.start(TOKEN)

asyncio.run(main())
