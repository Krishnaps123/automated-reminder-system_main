#ouqx gboz ampr cwjb-alert email
# ouqx gboz ampr cwjb-alert email
import os
import time
import sqlite3
import pytz
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# ============================================================
# LOAD ENV
# ============================================================
load_dotenv()

DB_PATH = os.getenv("DB_PATH")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASS = os.getenv("SENDER_PASS")

if not DB_PATH or not os.path.exists(DB_PATH):
    raise FileNotFoundError("❌ Database not found")
if not SENDER_EMAIL or not SENDER_PASS:
    raise ValueError("❌ Email credentials missing")

# ============================================================
# TIMEZONE
# ============================================================
IST = pytz.timezone("Asia/Kolkata")

# ============================================================
# SENT LOG
# ============================================================
SENT_LOG = "sent_email_reminders.log"

def load_sent():
    if os.path.exists(SENT_LOG):
        with open(SENT_LOG) as f:
            return set(line.strip() for line in f)
    return set()

def save_sent(sent):
    with open(SENT_LOG, "w") as f:
        for k in sorted(sent):
            f.write(k + "\n")

sent_reminders = load_sent()

# ============================================================
# EMAIL FUNCTION
# ============================================================
def send_email(recipient, subject, body):
    if "@example.com" in recipient.lower():
        return

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.send_message(msg)

        print(f"📧 Email sent → {recipient}")

    except Exception as e:
        print("❌ Email error:", e)

# ============================================================
# DB HELPERS
# ============================================================
def fetch_df(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_students():
    df = fetch_df("SELECT * FROM students")
    df["course"] = df["course"].str.strip().str.lower()
    df["batch_name"] = df["batch_name"].str.strip().str.upper()
    df["mode"] = df["mode"].str.strip().str.lower()
    df["year"] = df["year"].astype(str).str.strip()
    return df

def get_assignments():
    df = fetch_df("SELECT * FROM assignments")
    df["course"] = df["course"].str.strip().str.lower()
    df["batch_name"] = df["batch_name"].str.strip().str.upper()
    df["mode"] = df["mode"].fillna("offline").str.strip().str.lower()
    return df

def get_classes():
    return fetch_df("SELECT * FROM classes")

# ============================================================
# REMINDER LOOP
# ============================================================
def send_reminders():
    now = datetime.now(IST)
    print(f"\n⏰ Checking EMAIL reminders at {now.strftime('%Y-%m-%d %H:%M:%S')} IST")

    reminder_windows = {
        60: (45, 75),
        30: (20, 40),
        2:  (0, 5),
    }

    students_df = get_students()

    # ===================== CLASS REMINDERS =====================
    for _, row in get_classes().iterrows():
        class_dt = pd.to_datetime(
            f"{row['date']} {row['time']}",
            errors="coerce"
        )
        if pd.isna(class_dt):
            continue

        class_dt = class_dt.replace(tzinfo=IST)
        minutes_left = (class_dt - now).total_seconds() / 60
        if minutes_left < 0:
            continue

        for m, (lo, hi) in reminder_windows.items():
            if not (lo <= minutes_left <= hi):
                continue

            recipients = students_df[
                (students_df["course"] == row["course"].lower()) &
                (students_df["batch_name"] == row["batch_name"].upper()) &
                (students_df["mode"] == row["mode"].lower()) &
                (students_df["year"].str.contains("2025"))
            ]

            for _, stu in recipients.iterrows():
                key = f"class-{row['session_name']}-{row['date']}-{m}-{stu['email']}"
                if key in sent_reminders:
                    continue

                send_email(
                    stu["email"],
                    f"Class Reminder: {row['session_name']}",
                    f"Hi {stu['name']},\n\n"
                    f"📘 Upcoming Class Reminder\n\n"
                    f"📌 Topic : {row['session_name']}\n"
                    f"📚 Course: {row['course']}\n"
                    f"👥 Batch : {row['batch_name']} ({row['mode']})\n"
                    f"🕒 Starts in {m} minutes\n\n"
                    f"— Automated Reminder System"
                )

                sent_reminders.add(key)

    # ===================== ASSIGNMENT REMINDERS =====================
    for _, row in get_assignments().iterrows():
        raw_due = str(row["due_date"]).replace(".", ":").strip()
        if len(raw_due) <= 10:
            raw_due += " 23:59"

        due_dt = pd.to_datetime(
            raw_due,
            format="%Y-%m-%d %H:%M",
            errors="coerce"
        )
        if pd.isna(due_dt):
            continue

        due_dt = due_dt.replace(tzinfo=IST)
        minutes_left = (due_dt - now).total_seconds() / 60
        if minutes_left < 0:
            continue

        for m, (lo, hi) in reminder_windows.items():
            if not (lo <= minutes_left <= hi):
                continue

            recipients = students_df[
                (students_df["course"] == row["course"]) &
                (students_df["batch_name"] == row["batch_name"]) &
                (students_df["mode"] == row["mode"]) &
                (students_df["year"].str.contains("2025"))
            ]

            for _, stu in recipients.iterrows():
                key = f"assign-{row['subject']}-{row['due_date']}-{m}-{stu['email']}"
                if key in sent_reminders:
                    continue

                send_email(
                    stu["email"],
                    f"Assignment Reminder: {row['subject']}",
                    f"Hi {stu['name']},\n\n"
                    f"📝 Assignment Reminder\n\n"
                    f"📌 Topic : {row['subject']}\n"
                    f"📚 Course: {row['course'].upper()}\n"
                    f"👥 Batch : {row['batch_name']} ({row['mode']})\n"
                    f"⏳ Due in {m} minutes\n\n"
                    f"— Automated Reminder System"
                )

                sent_reminders.add(key)

    save_sent(sent_reminders)

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    print("📧 Email Reminder Scheduler Started...")
    while True:
        send_reminders()
        time.sleep(30)

