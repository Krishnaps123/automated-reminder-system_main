import sqlite3
import pandas as pd
import os

# -------------------------------------------------
# DATABASE PATH (PORTABLE & SAFE)
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "reminders.db")

def connect_db():
    # Ensure database directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

# -------------------------------------------------
# DATABASE TABLE CREATION
# -------------------------------------------------

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
        session_name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        mode TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course TEXT NOT NULL,
        batch_name TEXT,
        year INTEGER,
        subject TEXT NOT NULL,
        due_date TEXT NOT NULL,
        mode TEXT
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Tables verified or created successfully.")

# -------------------------------------------------
# VIEW FUNCTIONS
# -------------------------------------------------

def view_all():
    conn = connect_db()

    print("\n=== Students Table ===")
    print(pd.read_sql_query("SELECT * FROM students", conn))

    print("\n=== Classes Table ===")
    print(pd.read_sql_query("SELECT * FROM classes", conn))

    print("\n=== Assignments Table ===")
    print(pd.read_sql_query("SELECT * FROM assignments", conn))

    conn.close()

def view_by_course():
    course = input("Enter course name (e.g., DSA, CyberSecurity, FullStack): ").strip()
    batch_name = input("Enter batch name (optional, e.g., B4): ").strip()
    year = input("Enter year (optional, e.g., 2024 or 2025): ").strip()
    mode = input("Enter mode (Online/Offline, optional): ").strip()

    query = f"SELECT * FROM students WHERE course = '{course}'"

    if batch_name:
        query += f" AND batch_name = '{batch_name}'"

    if year:
        if year.isdigit():
            query += f" AND year = {year}"
        else:
            print("⚠️ Invalid year entered. Year must be numeric. Ignoring year filter.")

    if mode:
        query += f" AND mode = '{mode}'"

    conn = connect_db()

    print(f"\n=== Students Enrolled in {course} ===")
    print(pd.read_sql_query(query, conn))

    print(f"\n=== Classes for {course} ===")
    print(pd.read_sql_query(query.replace("students", "classes"), conn))

    print(f"\n=== Assignments for {course} ===")
    print(pd.read_sql_query(query.replace("students", "assignments"), conn))

    conn.close()

# -------------------------------------------------
# MENU
# -------------------------------------------------

def menu():
    create_tables()

    while True:
        print("\n🎓 Data Management Menu")
        print("1. View all data")
        print("2. View data by course/batch/year/mode")
        print("3. Exit")

        choice = input("\nEnter your choice: ")

        if choice == "1":
            view_all()
        elif choice == "2":
            view_by_course()
        elif choice == "3":
            print("👋 Exiting... Goodbye!")
            break
        else:
            print("❌ Invalid choice, please try again!")

# -------------------------------------------------
# ENTRY POINT
# -------------------------------------------------

if __name__ == "__main__":
    menu()
