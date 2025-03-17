import os
import json
import sqlite3
import threading
import subprocess
from datetime import datetime, timedelta
from tkinter import StringVar, Toplevel, messagebox, Tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# إعداد القفل لقفل العمليات على قاعدة البيانات
lock = threading.Lock()

# تحميل الإعدادات من ملف JSON
CONFIG_FILE = 'github_config.json'
DB_FILE = 'attendance.db'
EMPLOYEES = ["محمد مراد", "محمد مفيد", "محمد ممدوح", "مازن", "عبدو", "مرح", "ندي"]

# تحميل الإعدادات
def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

config = load_config()

# إعداد git
def setup_git():
    if not os.path.exists(".git"):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "remote", "add", "origin", config["repo_url"]])

# حفظ السجل في ملف نصي
def log_action(action):
    with open('log.txt', 'a', encoding='utf-8') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {action}\n")

# رفع البيانات على GitHub
def push_to_github():
    try:
        subprocess.run(["git", "add", DB_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Update attendance records"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        log_action("Data pushed to GitHub")
    except subprocess.CalledProcessError as e:
        log_action(f"Git push failed: {e}")

# سحب البيانات من GitHub
def pull_from_github():
    try:
        subprocess.run(["git", "pull", "origin", "main"], check=True)
        log_action("Data pulled from GitHub")
    except subprocess.CalledProcessError as e:
        log_action(f"Git pull failed: {e}")

# إنشاء قاعدة البيانات والجداول
def create_database():
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            employee_name TEXT,
                            day TEXT,
                            date TEXT,
                            entry_time TEXT,
                            exit_time TEXT,
                            work_hours REAL)
                        ''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS wages (
                            employee_name TEXT PRIMARY KEY,
                            wage REAL)
                        ''')
        conn.commit()
        conn.close()

# تسجيل الدخول
entry_times = {}
def log_entry(name):
    if not name:
        messagebox.showwarning("تنبيه", "يرجى اختيار اسم الموظف")
        return

    now = datetime.now()
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        entry_times[name] = now
        cursor.execute("INSERT INTO attendance (employee_name, day, date, entry_time) VALUES (?, ?, ?, ?)",
                       (name, now.strftime('%A'), now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')))
        conn.commit()
        conn.close()

    log_action(f"تسجيل دخول: {name}")
    push_to_github()
    messagebox.showinfo("نجاح", f"تم تسجيل دخول {name} بنجاح")

# تسجيل الخروج
def log_exit(name):
    if not name:
        messagebox.showwarning("تنبيه", "يرجى اختيار اسم الموظف")
        return

    if name not in entry_times:
        messagebox.showwarning("تنبيه", f"لم يتم تسجيل دخول {name}")
        return

    now = datetime.now()
    with lock:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        entry_time = entry_times.pop(name)
        work_hours = (now - entry_time).seconds / 3600

        cursor.execute("UPDATE attendance SET exit_time = ?, work_hours = ? WHERE employee_name = ? AND date = ? AND exit_time IS NULL",
                       (now.strftime('%H:%M:%S'), round(work_hours, 2), name, now.strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()

    log_action(f"تسجيل خروج: {name}")
    push_to_github()
    messagebox.showinfo("نجاح", f"تم تسجيل خروج {name} بنجاح")

# واجهة المستخدم الرئيسية
class AttendanceApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام تسجيل الحضور والانصراف")

        self.name_var = StringVar()

        self.label = ttk.Label(self, text="اسم الموظف:")
        self.label.pack()

        self.dropdown = ttk.Combobox(self, textvariable=self.name_var, values=EMPLOYEES)
        self.dropdown.pack()

        self.entry_btn = ttk.Button(self, text="تسجيل الدخول", command=lambda: log_entry(self.name_var.get()))
        self.entry_btn.pack()

        self.exit_btn = ttk.Button(self, text="تسجيل الخروج", command=lambda: log_exit(self.name_var.get()))
        self.exit_btn.pack()

# تشغيل البرنامج
if __name__ == "__main__":
    setup_git()
    pull_from_github()
    create_database()
    app = AttendanceApp()
    app.mainloop()
