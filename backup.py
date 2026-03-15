
import shutil, os
from datetime import datetime
from config import DB_NAME

def backup_db():
    os.makedirs("backup", exist_ok=True)
    now = datetime.now().strftime("%Y%m%d_%H%M")
    dst = f"backup/works_{now}.db"
    shutil.copy(DB_NAME, dst)
