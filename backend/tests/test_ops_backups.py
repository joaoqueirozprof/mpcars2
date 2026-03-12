from pathlib import Path


def _create_backup_dir(root: Path, backup_id: str) -> Path:
    backup_dir = root / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "database.sql").write_text("-- dump de teste\n", encoding="utf-8")
    (backup_dir / "assets.tar.gz").write_bytes(b"assets")
    (backup_dir / "manifest.txt").write_text(f"timestamp={backup_id}\n", encoding="utf-8")
    return backup_dir


def test_can_download_backup_artifacts(client, admin_headers, monkeypatch, tmp_path):
    from app.core.config import settings

    backup_root = tmp_path / "backups"
    _create_backup_dir(backup_root, "20260312_180000")

    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", str(backup_root))

    database_response = client.get(
        "/api/v1/ops/backups/20260312_180000/download/database",
        headers=admin_headers,
    )
    bundle_response = client.get(
        "/api/v1/ops/backups/20260312_180000/download/bundle",
        headers=admin_headers,
    )

    assert database_response.status_code == 200, database_response.text
    assert "database.sql" in database_response.headers["content-disposition"]
    assert database_response.text == "-- dump de teste\n"

    assert bundle_response.status_code == 200, bundle_response.text
    assert "backup-20260312_180000.tar.gz" in bundle_response.headers["content-disposition"]
    assert bundle_response.content


def test_can_sync_existing_backup_to_google_drive(client, admin_headers, monkeypatch, tmp_path):
    from app.core.config import settings
    from app.routers import ops

    backup_root = tmp_path / "backups"
    backup_dir = _create_backup_dir(backup_root, "20260312_181500")

    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", str(backup_root))
    monkeypatch.setattr(settings, "GOOGLE_DRIVE_BACKUP_ENABLED", True)
    monkeypatch.setattr(ops, "get_google_drive_service_account_email", lambda: "service-account@test")
    monkeypatch.setattr(ops, "get_google_drive_folder_url", lambda folder_id=None: "https://drive.google.com/drive/folders/root-folder")
    monkeypatch.setattr(
        ops,
        "sync_backup_directory",
        lambda path: {
            "status": "synced",
            "root_folder_id": "root-folder",
            "root_folder_url": "https://drive.google.com/drive/folders/root-folder",
            "backup_folder_id": "backup-folder",
            "backup_folder_url": "https://drive.google.com/drive/folders/backup-folder",
            "service_account_email": "service-account@test",
            "files": {
                "database.sql": {"url": "https://drive.google.com/file/d/database/view"},
                "assets.tar.gz": {"url": "https://drive.google.com/file/d/assets/view"},
                "manifest.txt": {"url": "https://drive.google.com/file/d/manifest/view"},
            },
        },
    )

    response = client.post(
        f"/api/v1/ops/backups/{backup_dir.name}/sync-google-drive",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "sincronizado"
    assert body["backup"]["google_drive"]["status"] == "synced"

    manifest = (backup_dir / "manifest.txt").read_text(encoding="utf-8")
    assert "google_drive_backup_folder_url=https://drive.google.com/drive/folders/backup-folder" in manifest
