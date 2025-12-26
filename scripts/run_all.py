import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable  # uses venv python automatically

discord_script = os.path.join(BASE_DIR, "scripts", "discord_notifier.py")
email_script = os.path.join(BASE_DIR, "scripts", "mail_scheduler.py")

# Start Discord bot
subprocess.Popen([PYTHON, discord_script])

# Start Email scheduler
subprocess.Popen([PYTHON, email_script])

# Keep the launcher alive
import time
while True:
    time.sleep(60)
