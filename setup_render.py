import os
import subprocess
from pathlib import Path

print("=== Patriot-M Render Setup ===")

project_path = Path(__file__).parent

# --------------------------------
# 1. requirements.txt проверка
# --------------------------------

req = project_path / "requirements.txt"

if not req.exists():
    print("Создаю requirements.txt")

    req.write_text(
"""python-telegram-bot==20.7
python-dotenv
flask
gspread
oauth2client
gunicorn
"""
    )

# --------------------------------
# 2. Procfile для Render
# --------------------------------

procfile = project_path / "Procfile"

if not procfile.exists():
    print("Создаю Procfile")

    procfile.write_text(
"""worker: python bot.py"""
    )

# --------------------------------
# 3. runtime.txt
# --------------------------------

runtime = project_path / "runtime.txt"

if not runtime.exists():
    print("Создаю runtime.txt")

    runtime.write_text(
"""python-3.11.9"""
    )

# --------------------------------
# 4. проверка .env
# --------------------------------

env_file = project_path / ".env"

if not env_file.exists():
    print("⚠ .env не найден. Создаю пример")

    env_file.write_text(
"""BOT_TOKEN=
OWNER_ID=
REPORT_ID=
GOOGLE_SHEET_ID=
"""
    )

# --------------------------------
# 5. установка библиотек
# --------------------------------

print("Устанавливаю библиотеки")

subprocess.run(
    ["pip", "install", "-r", "requirements.txt"]
)

# --------------------------------
# 6. тестовый запуск
# --------------------------------

print("Пробный запуск бота")

try:
    subprocess.run(["python", "bot.py"])
except:
    print("Бот завершился")

print("=== Готово ===")