import sys
from pathlib import Path

from app.services.google_drive_backup import GoogleDriveBackupError, sync_backup_directory


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python -m app.scripts.sync_backup_to_google_drive /caminho/do/backup")
        return 1

    backup_dir = Path(sys.argv[1]).resolve()

    try:
        result = sync_backup_directory(backup_dir)
    except GoogleDriveBackupError as exc:
        print(str(exc))
        return 2

    print(
        result.get("backup_folder_url")
        or result.get("root_folder_url")
        or "Backup sincronizado no Google Drive."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
