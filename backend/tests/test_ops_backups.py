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
    monkeypatch.setattr(ops, "is_google_drive_enabled", lambda db=None: True)
    monkeypatch.setattr(
        ops,
        "get_google_drive_overview",
        lambda db=None: {
            "enabled": True,
            "configured": True,
            "sync_on_backup": True,
            "auth_mode": "service_account",
            "folder_id": "root-folder",
            "folder_url": "https://drive.google.com/drive/folders/root-folder",
            "folder_name": "Backups",
            "account_email": "service-account@test",
            "service_account_email": "service-account@test",
            "client_id_configured": False,
            "pending_authorization": {"pending": False},
        },
    )
    monkeypatch.setattr(
        ops,
        "sync_backup_directory",
        lambda path: {
            "status": "synced",
            "root_folder_id": "root-folder",
            "root_folder_url": "https://drive.google.com/drive/folders/root-folder",
            "backup_folder_id": "backup-folder",
            "backup_folder_url": "https://drive.google.com/drive/folders/backup-folder",
            "account_email": "service-account@test",
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


def test_can_start_google_drive_oauth_device_flow(client, admin_headers, monkeypatch):
    from app.routers import ops

    monkeypatch.setattr(
        ops,
        "start_google_drive_device_authorization",
        lambda client_id, client_secret, folder_name=None, db=None: {
            "status": "authorization_pending",
            "message": "Abra o Google e informe o codigo.",
            "user_code": "ABCD-EFGH",
            "verification_url": "https://www.google.com/device",
            "expires_at": "2026-03-12T19:30:00+00:00",
            "interval_seconds": 5,
            "folder_name": folder_name or "MPCARS Backups",
        },
    )

    response = client.post(
        "/api/v1/ops/google-drive/oauth/device/start",
        headers=admin_headers,
        json={
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": "client-secret",
            "folder_name": "Backups MPCARS",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "authorization_pending"
    assert body["user_code"] == "ABCD-EFGH"


def test_can_poll_google_drive_oauth_device_flow(client, admin_headers, monkeypatch):
    from app.routers import ops

    monkeypatch.setattr(
        ops,
        "poll_google_drive_device_authorization",
        lambda db=None: {
            "status": "connected",
            "message": "Google Drive conectado com sucesso.",
            "account_email": "cliente@gmail.com",
            "folder_id": "root-folder",
            "folder_url": "https://drive.google.com/drive/folders/root-folder",
            "connected_at": "2026-03-12T19:35:00+00:00",
            "auth_mode": "oauth",
        },
    )

    response = client.post(
        "/api/v1/ops/google-drive/oauth/device/poll",
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "connected"
    assert body["account_email"] == "cliente@gmail.com"
