#ouqx gboz ampr cwjb-alert email
# ouqx gboz ampr cwjb-alert email
import os
import time
import pytz
import smtplib
import psycopg2
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================================
# EMAIL CREDS (RAILWAY VARIABLES)
# ============================================================

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASS = os.getenv("SENDER_PASS")

if not SENDER_EMAIL or not SENDER_PASS:
    raise RuntimeError("❌ Email credentials missing")

# ============================================================
# TIMEZONE
# ============================================================

IST = pytz.timezone("Asia/Kolkata")

# ============================================================
# DATABASE CONNECTION (LAZY / RUNTIME SAFE)
# ============================================================

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("❌ DATABASE_URL not found at runtime")
    return psycopg2.connect(database_url)

# ============================================================
# SENT REMINDERS (POSTGRESQL - PERSISTENT)
# ============================================================

def load_sent():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT reminder_key FROM sent_reminders")
            return {r[0] for r in cur.fetchall()}

def mark_sent(key):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sent_reminders (reminder_key) VALUES (%s) ON CONFLICT DO NOTHING",
                (key,)
            )
            conn.commit()

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
# DB HELPERS (POSTGRESQL + PANDAS)
# ============================================================

def fetch_df(query):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)

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

def send_reminders(sent_reminders):
    now = datetime.now(IST)
    print(f"\n⏰ Checking EMAIL reminders at {now:%Y-%m-%d %H:%M:%S} IST")

    reminder_windows = {
        60: (45, 75),
        30: (20, 40),
        2:  (0, 5),
    }

    students_df = get_students()

    # ===================== CLASS REMINDERS =====================
    for _, row in get_classes().iterrows():
        class_dt = pd.to_datetime(f"{row['date']} {row['time']}", errors="coerce")
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

                mark_sent(key)
                sent_reminders.add(key)

    # ===================== ASSIGNMENT REMINDERS =====================
    for _, row in get_assignments().iterrows():
        raw_due = str(row["due_date"]).replace(".", ":").strip()
        if len(raw_due) <= 10:
            raw_due += " 23:59"

        due_dt = pd.to_datetime(raw_due, format="%Y-%m-%d %H:%M", errors="coerce")
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

                mark_sent(key)
                sent_reminders.add(key)

# ============================================================
# RUN (WORKER MODE)
# ============================================================

if __name__ == "__main__":
    print("📧 Email Reminder Scheduler Started...")
    sent_reminders = load_sent()

    while True:
        send_reminders(sent_reminders)
        time.sleep(30)
