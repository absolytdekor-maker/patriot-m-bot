import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_FILE
from datetime import datetime

def добавить_в_google(имя, код_операции, количество, ставка, сумма, user_id):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        if not sheet.get_all_values():
            sheet.append_row(["Дата", "Сотрудник", "Операция", "Кол-во", "Ставка", "Сумма", "User ID"])
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([now, имя, код_операции, количество, ставка or "", сумма or "", user_id])
    except Exception as e:
        print(f"Ошибка записи в Google Таблицу: {e}")