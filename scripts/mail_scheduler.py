#ouqx gboz ampr cwjb-alert email
import os
import time
import pytz
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
SENT_FILE = os.path.join(DATA_DIR, "sent_reminders.xlsx")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASS = os.getenv("SENDER_PASS")

IST = pytz.timezone("Asia/Kolkata")

# ============================================================
# EMAIL
# ============================================================
def send_email(to, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.send_message(msg)

    print(f"✅ Email sent → {to}")

# ============================================================
# SENT TRACKING
# ============================================================
def reminder_already_sent(key):
    if not os.path.exists(SENT_FILE):
        return False
    df = pd.read_excel(SENT_FILE)
    return key in df["key"].values

def mark_reminder_sent(key):
    if os.path.exists(SENT_FILE):
        df = pd.read_excel(SENT_FILE)
    else:
        df = pd.DataFrame(columns=["key"])

    if key not in df["key"].values:
        df.loc[len(df)] = key
        df.to_excel(SENT_FILE, index=False)

# ============================================================
# FILENAME METADATA
# ============================================================
def parse_filename(filename):
    name = os.path.splitext(filename)[0]
    course, batch, year, mode = name.split("_")
    return course.lower(), batch.lower(), str(year), mode.lower()

# ============================================================
# PROCESS FILE
# ============================================================
def process_file(filepath):
    filename = os.path.basename(filepath)
    course, batch, year, mode = parse_filename(filename)

    print(f"\n📘 Processing {filename}")

    xls = pd.ExcelFile(filepath)
    students = pd.read_excel(xls, "students")
    schedule = pd.read_excel(xls, "schedule")
    assignments = pd.read_excel(xls, "assignment")

    # Normalize students
    students["year"] = students["year"].astype(str)
    for col in ["course", "batch_name", "mode"]:
        students[col] = students[col].astype(str).str.lower().str.strip()

    recipients = students[
        (students["course"] == course)
        & (students["batch_name"] == batch)
        & (students["year"] == year)
        & (students["mode"] == mode)
    ]

    now = datetime.now(IST)

    # ========================================================
    # CLASS REMINDERS (60 / 30 / 2 MIN) — SAME AS DISCORD
    # ========================================================
    CLASS_WINDOWS = {
        60: (55, 65),
        30: (25, 35),
        2:  (0, 3),
    }

    for _, row in schedule.iterrows():
        try:
            class_dt = pd.to_datetime(
                f"{row['date']} {row['time']}",
                errors="coerce"
            )
            if pd.isna(class_dt):
                continue

            class_dt = IST.localize(class_dt)
            minutes_left = (class_dt - now).total_seconds() / 60

            for mins, (low, high) in CLASS_WINDOWS.items():
                if not (low <= minutes_left <= high):
                    continue

                key = f"class-{mins}-{row['session_name']}-{row['date']}"
                if reminder_already_sent(key):
                    continue

                for _, stu in recipients.iterrows():
                    body = (
                        f"Hi {stu['name']},\n\n"
                        f"📚 Class Reminder\n"
                        f"Session: {row['session_name']}\n"
                        f"Starts at: {class_dt.strftime('%I:%M %p on %d-%b-%Y')}\n\n"
                        f"⏰ {mins} minutes remaining\n\n"
                        f"— Automated Reminder System"
                    )
                    send_email(
                        stu["email"],
                        f"Class Reminder: {row['session_name']}",
                        body,
                    )

                mark_reminder_sent(key)

        except Exception as e:
            print("⚠️ Class error:", e)

    # ========================================================
    # ASSIGNMENT REMINDERS (60 / 30 / 15 MIN)
    # ========================================================
    ASSIGN_WINDOWS = {
        60: (58, 62),
        30: (28, 32),
        15: (13, 17),
    }

    for _, row in assignments.iterrows():
        try:
            due_dt = pd.to_datetime(row["due_date"], errors="coerce")
            if pd.isna(due_dt):
                continue

            if due_dt.hour == 0:
                due_dt = due_dt.replace(hour=9)

            due_dt = IST.localize(due_dt)
            minutes_left = (due_dt - now).total_seconds() / 60

            for mins, (low, high) in ASSIGN_WINDOWS.items():
                if not (low <= minutes_left <= high):
                    continue

                key = f"assign-{row['subject']}-{mins}"
                if reminder_already_sent(key):
                    continue

                for _, stu in recipients.iterrows():
                    body = (
                        f"Hi {stu['name']},\n\n"
                        f"📝 Assignment Reminder\n"
                        f"Subject: {row['subject']}\n"
                        f"Due at: {due_dt.strftime('%I:%M %p on %d-%b-%Y')}\n\n"
                        f"⏳ {mins} minutes remaining\n\n"
                        f"— Automated Reminder System"
                    )
                    send_email(
                        stu["email"],
                        f"Assignment Reminder: {row['subject']}",
                        body,
                    )

                mark_reminder_sent(key)

        except Exception as e:
            print("⚠️ Assignment error:", e)

# ============================================================
# MAIN LOOP
# ============================================================
if __name__ == "__main__":
    print("📧 Email Reminder System Started")

    while True:
        try:
            for file in os.listdir(DATA_DIR):
                if file.endswith(".xlsx") and file != "sent_reminders.xlsx":
                    process_file(os.path.join(DATA_DIR, file))
        except Exception as e:
            print("❌ Error:", e)

        time.sleep(10)  # SAME AS DISCORD
