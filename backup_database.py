from datetime import datetime
from pathlib import Path
import shutil

DATABASE_FILE = Path("database.db")
INSTANCE_DATABASE_FILE = Path("instance/database.db")
BACKUP_DIR = Path("backups")


def find_database_file():
    if DATABASE_FILE.exists():
        return DATABASE_FILE

    if INSTANCE_DATABASE_FILE.exists():
        return INSTANCE_DATABASE_FILE

    return None


def backup_database():
    print("Starting Gymothy database backup...")

    BACKUP_DIR.mkdir(exist_ok=True)

    database_file = find_database_file()

    if database_file is None:
        print("Backup failed: no database file was found.")
        print("Checked: database.db and instance/database.db")
        return None

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = BACKUP_DIR / f"gymothy_backup_{timestamp}.db"

    shutil.copy2(database_file, backup_file)

    print(f"Backup created successfully: {backup_file}")
    return backup_file


if __name__ == "__main__":
    backup_database()