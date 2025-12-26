import os
import asyncio
import sqlite3
import pandas as pd
from datetime import datetime
import discord
from dotenv import load_dotenv
import ssl
import aiohttp

# ============================================================
# SENT REMINDER LOG
# ============================================================
SENT_LOG_PATH = "sent_discord_reminders.log"

def load_sent_log():
    if os.path.exists(SENT_LOG_PATH):
        with open(SENT_LOG_PATH, "r") as f:
            return set(line.strip() for line in f)
    return set()

def save_sent_log(sent):
    with open(SENT_LOG_PATH, "w") as f:
        for k in sorted(sent):
            f.write(k + "\n")

sent_reminders = load_sent_log()

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DB_PATH = os.getenv("DB_PATH")

if not TOKEN or not CHANNEL_ID or not DB_PATH:
    raise ValueError("❌ Missing .env values")

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
# SEND MESSAGE
# ============================================================
async def send_message(channel, message):
    try:
        await channel.send(message)
        print("✅ Sent reminder")
    except Exception as e:
        print("❌ Discord send error:", e)

# ============================================================
# REMINDER LOOP
# ============================================================
async def reminder_loop():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        print("❌ Channel not found")
        return

    print("🔁 Discord Reminder System Started")

    while not bot.is_closed():
        now = datetime.now()

        # ====================================================
        # CLASS REMINDERS (60 / 30 / 2 MIN)
        # ====================================================
        classes_df = get_classes()

        for _, row in classes_df.iterrows():
            try:
                class_dt = pd.to_datetime(
                    f"{row['date']} {row['time']}",
                    errors="coerce"
                )

                if pd.isna(class_dt):
                    continue

                minutes_left = (class_dt - now).total_seconds() / 60

                print(
                    f"[DEBUG] Class '{row['session_name']}' "
                    f"starts in {minutes_left:.2f} minutes"
                )

                # -------- 1 HOUR BEFORE --------
                if 55 <= minutes_left <= 65:
                    key = f"class-60-{row['session_name']}-{row['date']}"
                    if key not in sent_reminders:
                        msg = (
                            f"⏰ **Class Reminder (1 Hour Left)**\n\n"
                            f"📘 {row['session_name']}\n"
                            f"📚 {row['course']}\n"
                            f"👥 {row.get('batch_name','')} ({row.get('mode','')})\n"
                            f"🕒 Starts at {row['time']}"
                        )
                        await send_message(channel, msg)
                        sent_reminders.add(key)

                # -------- 30 MIN BEFORE --------
                if 25 <= minutes_left <= 35:
                    key = f"class-30-{row['session_name']}-{row['date']}"
                    if key not in sent_reminders:
                        msg = (
                            f"⏰ **Class Reminder (30 Minutes Left)**\n\n"
                            f"📘 {row['session_name']}\n"
                            f"📚 {row['course']}\n"
                            f"👥 {row.get('batch_name','')} ({row.get('mode','')})\n"
                            f"🕒 Starts at {row['time']}"
                        )
                        await send_message(channel, msg)
                        sent_reminders.add(key)

                # -------- 2 MIN BEFORE --------
                if 0 <= minutes_left <= 3:
                    key = f"class-2-{row['session_name']}-{row['date']}"
                    if key not in sent_reminders:
                        msg = (
                            f"🚀 **Class Starting Soon (2 Minutes!)**\n\n"
                            f"📘 {row['session_name']}\n"
                            f"📚 {row['course']}\n"
                            f"👥 {row.get('batch_name','')} ({row.get('mode','')})\n"
                            f"🎓 Join now!"
                        )
                        await send_message(channel, msg)
                        sent_reminders.add(key)

            except Exception as e:
                print("⚠️ Class reminder error:", e)

        # ====================================================
        # ASSIGNMENT REMINDERS (60 / 30 / 15 MIN)
        # ====================================================
        assignments_df = get_assignments()

        for _, row in assignments_df.iterrows():
            try:
                due_dt = pd.to_datetime(row["due_date"], errors="coerce")
                if pd.isna(due_dt):
                    continue

                minutes_left = (due_dt - now).total_seconds() / 60

                for m in (60, 30, 15):
                    if not (m - 2 <= minutes_left <= m + 2):
                        continue

                    key = f"assign-{row['subject']}-{m}"
                    if key in sent_reminders:
                        continue

                    msg = (
                        f"📝 **Assignment Reminder**\n\n"
                        f"📌 {row['subject']}\n"
                        f"📚 {row['course']}\n"
                        f"👥 {row.get('batch_name','')} ({row.get('mode','')})\n"
                        f"⏳ {m} minutes remaining"
                    )
                    await send_message(channel, msg)
                    sent_reminders.add(key)

            except Exception as e:
                print("⚠️ Assignment reminder error:", e)

        save_sent_log(sent_reminders)
        await asyncio.sleep(10)

# ============================================================
# DISCORD EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"🤖 Logged in as {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("✅ Discord Reminder Bot Online")

@bot.event
async def setup_hook():
    asyncio.create_task(reminder_loop())

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
# RUN BOT
# ============================================================
bot.run(TOKEN)
