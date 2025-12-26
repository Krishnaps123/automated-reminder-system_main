# import os
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()
# SENDER_EMAIL = os.getenv("SENDER_EMAIL")
# SENDER_PASS = os.getenv("SENDER_PASS")

# if not SENDER_EMAIL or not SENDER_PASS:
#     raise ValueError("❌ Missing SENDER_EMAIL or SENDER_PASS in .env file!")

# # Replace with your email for testing
# TEST_RECIPIENT = "navamib2023@gmail.com"

# # Compose email
# subject = "✅ Test Email from Automated Reminder System"
# body = (
#     "Hi there,\n\n"
#     "This is a test email from your automated reminder system to confirm that Gmail integration works.\n\n"
#     "— Automated Reminder System"
# )

# msg = MIMEMultipart()
# msg["From"] = SENDER_EMAIL
# msg["To"] = TEST_RECIPIENT
# msg["Subject"] = subject
# msg.attach(MIMEText(body, "plain"))

# # Send email
# try:
#     with smtplib.SMTP("smtp.gmail.com", 587) as server:
#         server.starttls()
#         server.login(SENDER_EMAIL, SENDER_PASS)
#         server.send_message(msg)
#     print(f"✅ Test email sent successfully to {TEST_RECIPIENT}")
# except Exception as e:
#     print(f"❌ Error sending test email: {e}")


import sqlite3

DB_PATH = r"D:\trailnew\automated_reminder_system-main\database\reminders.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
INSERT INTO classes (course, batch_name, year, session_name, date, time, mode)
VALUES ('Scheduled', 'A', 2025, 'Evening Class (6 PM)', '2025-12-02', '18:00', 'Online');
""")

conn.commit()
conn.close()

print("✅ Test class inserted successfully!")
