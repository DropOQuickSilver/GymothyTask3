import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
import shutil
import sys


class DatabaseBackup:

    CANDIDATE_PATHS = [Path("database.db"), Path("instance/database.db")]

    def __init__(self, backup_dir="backups", keep=5):
        self.backup_dir = Path(backup_dir)
        self.keep = keep
        self.log_file = self.backup_dir / "backup_log.txt"

    def find_database_file(self):
        for path in self.CANDIDATE_PATHS:
            if path.exists():
                return path
        return None

    def verify_integrity(self, db_path):
        try:
            connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            result = connection.execute("PRAGMA integrity_check;").fetchone()
            connection.close()
            return result is not None and result[0] == "ok"
        except sqlite3.Error:
            return False

    def apply_retention_policy(self):
        backups = sorted(
            self.backup_dir.glob("gymothy_backup_*.db"),
            key=lambda path: path.stat().st_mtime,
        )

        removed = []
        while len(backups) > self.keep:
            oldest = backups.pop(0)
            oldest.unlink()
            removed.append(oldest.name)

        return removed

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as log_handle:
            log_handle.write(f"[{timestamp}] {message}\n")

    def run(self):
        self.backup_dir.mkdir(exist_ok=True)

        source = self.find_database_file()
        if source is None:
            self.log("FAILED - no database file found (checked database.db, instance/database.db)")
            print("Backup failed: no database file was found.")
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destination = self.backup_dir / f"gymothy_backup_{timestamp}.db"

        source_size = source.stat().st_size
        shutil.copy2(source, destination)
        destination_size = destination.stat().st_size

        if source_size != destination_size:
            self.log(f"FAILED - size mismatch copying {source} -> {destination}")
            print("Backup failed: copied file size does not match source.")
            destination.unlink(missing_ok=True)
            return None

        if not self.verify_integrity(destination):
            self.log(f"FAILED - integrity check failed for {destination}")
            print("Backup failed: integrity check did not pass.")
            destination.unlink(missing_ok=True)
            return None

        removed = self.apply_retention_policy()

        self.log(
            f"SUCCESS - {destination.name} ({destination_size} bytes, integrity OK)"
            + (f" | removed old backups: {', '.join(removed)}" if removed else "")
        )

        print(f"Backup created successfully: {destination}")
        print(f"Integrity check passed. Size: {destination_size} bytes.")
        if removed:
            print(f"Retention policy removed {len(removed)} old backup(s): {', '.join(removed)}")

        return destination


def main():
    parser = argparse.ArgumentParser(description="Back up the Gymothy database.")
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Number of recent backups to retain (default: 5).",
    )
    args = parser.parse_args()

    backup = DatabaseBackup(keep=args.keep)
    result = backup.run()

    sys.exit(0 if result is not None else 1)


if __name__ == "__main__":
    main()