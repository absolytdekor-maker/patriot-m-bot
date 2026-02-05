import sqlite3
import os
import csv
from datetime import datetime

ИМЯ_БАЗЫ = "works.db"

def инициализировать_базу():
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()

    курсор.execute("""
        CREATE TABLE IF NOT EXISTS пользователи (
            id INTEGER PRIMARY KEY,
            имя TEXT,
            админ BOOLEAN DEFAULT 0
        )
    """)

    курсор.execute("""
        CREATE TABLE IF NOT EXISTS расценки (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            код TEXT UNIQUE NOT NULL,
            ставка REAL NOT NULL,
            единица TEXT NOT NULL DEFAULT 'шт'
        )
    """)

    курсор.execute("""
        CREATE TABLE IF NOT EXISTS работы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            пользователь_id INTEGER NOT NULL,
            имя TEXT,
            код_операции TEXT NOT NULL,
            количество REAL NOT NULL DEFAULT 1,
            дата TEXT NOT NULL
        )
    """)

    соединение.commit()
    соединение.close()

def добавить_пользователя(id: int, имя: str = None, админ: bool = False):
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute(
        "INSERT OR REPLACE INTO пользователи (id, имя, админ) VALUES (?, ?, ?)",
        (id, имя or f"пользователь_{id}", int(админ))
    )
    соединение.commit()
    соединение.close()

def проверить_доступ(id: int) -> bool:
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute("SELECT 1 FROM пользователи WHERE id = ?", (id,))
    return курсор.fetchone() is not None

def проверить_админа(id: int) -> bool:
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute("SELECT админ FROM пользователи WHERE id = ?", (id,))
    строка = курсор.fetchone()
    return bool(строка[0]) if строка else False

def установить_расценку(код: str, ставка: float, единица: str = "шт"):
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute(
        "INSERT OR REPLACE INTO расценки (код, ставка, единица) VALUES (?, ?, ?)",
        (код, ставка, единица)
    )
    соединение.commit()
    соединение.close()

def получить_расценку(код: str):
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute("SELECT ставка, единица FROM расценки WHERE код = ?", (код,))
    return курсор.fetchone()

def получить_все_расценки():
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute("SELECT код, ставка, единица FROM расценки")
    return курсор.fetchall()

def добавить_работу(пользователь_id: int, имя: str, код_операции: str, количество: float = 1):
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute(
        "INSERT INTO работы (пользователь_id, имя, код_операции, количество, дата) VALUES (?, ?, ?, ?, ?)",
        (пользователь_id, имя, код_операции, количество, datetime.now().isoformat())
    )
    соединение.commit()
    соединение.close()

def получить_работы_до_сегодня(пользователь_id: int):
    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    сейчас = datetime.now()
    курсор.execute("""
        SELECT код_операции, количество, дата
        FROM работы
        WHERE пользователь_id = ?
          AND strftime('%Y', дата) = ?
          AND strftime('%m', дата) = ?
          AND CAST(strftime('%d', дата) AS INTEGER) <= ?
        ORDER BY дата
    """, (пользователь_id, str(сейчас.year), f"{сейчас.month:02d}", сейчас.day))
    return курсор.fetchall()

def экспорт_в_csv(месяц: int = None, год: int = None) -> str:
    if месяц is None or год is None:
        сейчас = datetime.now()
        месяц = сейчас.month
        год = сейчас.year

    имя_файла = f"экспорт_{год}_{месяц:02d}.csv"
    путь = os.path.join("exports", имя_файла)
    os.makedirs("exports", exist_ok=True)

    соединение = sqlite3.connect(ИМЯ_БАЗЫ)
    курсор = соединение.cursor()
    курсор.execute("""
        SELECT w.дата, u.имя, w.код_операции, w.количество, r.ставка
        FROM работы w
        JOIN пользователи u ON w.пользователь_id = u.id
        LEFT JOIN расценки r ON w.код_операции = r.код
        WHERE strftime('%Y', w.дата) = ? AND strftime('%m', w.дата) = ?
        ORDER BY w.дата
    """, (str(год), f"{месяц:02d}"))

    with open(путь, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата", "Сотрудник", "Операция", "Кол-во", "Ставка", "Сумма"])
        for строка in курсор.fetchall():
            дата, имя, код, колво, ставка = строка
            ставка = ставка or 0
            сумма = колво * ставка
            writer.writerow([дата[:19], имя, код, колво, ставка, round(сумма, 2)])

    соединение.close()
    return путь