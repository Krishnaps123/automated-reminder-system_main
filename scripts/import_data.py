
import sqlite3
import pandas as pd
import os

# ----------------------------------------------------------
# Paths
# ----------------------------------------------------------
DB_PATH = r"D:\trailnew\automated_reminder_system-main\database\reminders.db"
DATA_DIR = r"D:\trailnew\automated_reminder_system-main\data"


# ----------------------------------------------------------
# Database connection
# ----------------------------------------------------------
def connect_db():
    return sqlite3.connect(DB_PATH)


# ----------------------------------------------------------
# Create tables if not exist
# ----------------------------------------------------------
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        discord_id TEXT,
        course TEXT NOT NULL,
        batch_name TEXT,
        year INTEGER,
        mode TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        class_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course TEXT NOT NULL,
        batch_name TEXT,
        year INTEGER,
        mode TEXT,
        session_name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course TEXT NOT NULL,
        batch_name TEXT,
        year INTEGER,
        mode TEXT,
        subject TEXT NOT NULL,
        due_date TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Tables verified or created successfully.")


# ----------------------------------------------------------
# Import students
# ----------------------------------------------------------
def import_students(course, batch, year, mode, file_path):
    print(f"📥 Importing students from {file_path} ...")
    conn = connect_db()

    try:
        df = pd.read_excel(file_path, sheet_name="students")
    except Exception:
        conn.close()
        return

    if "student_id" in df.columns:
        df = df.drop(columns=["student_id"])

    df.columns = [c.strip().lower() for c in df.columns]
    df["course"] = course
    df["batch_name"] = batch
    df["year"] = year
    df["mode"] = mode

    conn.execute(
        "DELETE FROM students WHERE course=? AND batch_name=? AND year=?",
        (course, batch, year)
    )
    conn.commit()

    df.to_sql("students", conn, if_exists="append", index=False)
    conn.close()
    print(f"✅ Imported {len(df)} students for {course}-{batch}-{year} ({mode})")


# ----------------------------------------------------------
# Import classes
# ----------------------------------------------------------
def import_classes(course, batch, year, mode, file_path):
    print(f"📘 Importing classes from {file_path} ...")
    conn = connect_db()

    try:
        df = pd.read_excel(file_path, sheet_name="schedule")
    except Exception:
        conn.close()
        return

    if "class_id" in df.columns:
        df = df.drop(columns=["class_id"])

    df.columns = [c.strip().lower() for c in df.columns]
    df["course"] = course
    df["batch_name"] = batch
    df["year"] = year
    df["mode"] = mode

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    def parse_time(val):
        if pd.isna(val):
            return "09:00"
        val = str(val).split(".")[0]
        try:
            return pd.to_datetime(val).strftime("%H:%M")
        except:
            return "09:00"

    df["time"] = df["time"].apply(parse_time)

    conn.execute(
        "DELETE FROM classes WHERE course=? AND batch_name=? AND year=?",
        (course, batch, year)
    )
    conn.commit()

    df.to_sql("classes", conn, if_exists="append", index=False)
    conn.close()
    print(f"✅ Imported {len(df)} classes for {course}-{batch}-{year} ({mode})")


# ----------------------------------------------------------
# Import assignments
# ----------------------------------------------------------
def import_assignments(course, batch, year, mode, file_path):
    print(f"📗 Importing assignments from {file_path} ...")
    conn = connect_db()

    try:
        df = pd.read_excel(file_path, sheet_name="assignment")
    except Exception:
        conn.close()
        return

    if "assignment_id" in df.columns:
        df = df.drop(columns=["assignment_id"])

    df.columns = [c.strip().lower() for c in df.columns]
    df["course"] = course
    df["batch_name"] = batch
    df["year"] = year
    df["mode"] = mode

    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    conn.execute(
        "DELETE FROM assignments WHERE course=? AND batch_name=? AND year=?",
        (course, batch, year)
    )
    conn.commit()

    df.to_sql("assignments", conn, if_exists="append", index=False)
    conn.close()
    print(f"✅ Imported {len(df)} assignments for {course}-{batch}-{year} ({mode})")


# ----------------------------------------------------------
# Import all Excel files
# ----------------------------------------------------------
def import_all_courses():
    create_tables()

    for file in os.listdir(DATA_DIR):

        # only Excel files
        if not file.endswith(".xlsx"):
            continue

        # skip internal tracking file
        if file.lower() == "sent_reminders.xlsx":
            continue

        try:
            base = file.replace(".xlsx", "")
            parts = base.split("_")

            course = parts[0]
            batch = parts[1]
            year = parts[2]

            mode = "Online" if "online" in base.lower() else "Offline"
            print(f"📄 Detected mode: {mode} for file '{file}'")

            file_path = os.path.join(DATA_DIR, file)

            import_students(course, batch, year, mode, file_path)
            import_classes(course, batch, year, mode, file_path)
            import_assignments(course, batch, year, mode, file_path)

        except Exception as e:
            print(f"❌ Error processing {file}: {e}")

    print("\n🎓 All data imported successfully!")


# ----------------------------------------------------------
# Run
# ----------------------------------------------------------
if __name__ == "__main__":
    import_all_courses()
