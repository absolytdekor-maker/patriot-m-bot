
import sqlite3
from datetime import datetime
from config import DB_NAME

def db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        name TEXT,
        admin INTEGER DEFAULT 0
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS rates(
        code TEXT PRIMARY KEY,
        rate REAL,
        unit TEXT DEFAULT 'шт'
    )
    ''')

    cur.execute('''
    CREATE TABLE IF NOT EXISTS works(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        operation TEXT,
        quantity REAL,
        date TEXT
    )
    ''')

    conn.commit()
    conn.close()

def add_user(uid, name, admin=False):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO users VALUES(?,?,?)",
        (uid, name, int(admin))
    )
    conn.commit()
    conn.close()

def has_access(uid):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE id=?", (uid,))
    r = cur.fetchone()
    conn.close()
    return r is not None

def get_rate(code):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT rate, unit FROM rates WHERE code=?", (code,))
    r = cur.fetchone()
    conn.close()
    return r

def set_rate(code, rate, unit="шт"):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO rates VALUES(?,?,?)",(code,rate,unit))
    conn.commit()
    conn.close()

def get_rates():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT code, rate, unit FROM rates")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_work(uid, username, op, qty):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO works(user_id,username,operation,quantity,date) VALUES(?,?,?,?,?)",
        (uid,username,op,qty,datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def delete_last(uid):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM works WHERE user_id=? ORDER BY date DESC LIMIT 1",(uid,))
    r = cur.fetchone()
    if r:
        cur.execute("DELETE FROM works WHERE id=?",(r[0],))
    conn.commit()
    conn.close()
