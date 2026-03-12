import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.core.config import settings


GOOGLE_DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive"]
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDriveBackupError(RuntimeError):
    pass


def _service_account_file_path() -> Optional[Path]:
    if not settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE:
        return None

    configured = Path(settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE)
    if configured.is_absolute():
        return configured

    return (Path(__file__).resolve().parents[2] / configured).resolve()


def _load_service_account_info() -> Optional[Dict[str, Any]]:
    if settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON:
        try:
            return json.loads(settings.GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            return None

    service_account_file = _service_account_file_path()
    if service_account_file and service_account_file.exists():
        try:
            return json.loads(service_account_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    return None


def is_google_drive_enabled() -> bool:
    return bool(settings.GOOGLE_DRIVE_BACKUP_ENABLED)


def is_google_drive_configured() -> bool:
    return bool(
        settings.GOOGLE_DRIVE_BACKUP_ENABLED
        and settings.GOOGLE_DRIVE_FOLDER_ID
        and _load_service_account_info()
    )


def get_google_drive_folder_url(folder_id: Optional[str] = None) -> Optional[str]:
    effective_folder_id = (folder_id or settings.GOOGLE_DRIVE_FOLDER_ID or "").strip()
    if not effective_folder_id:
        return None
    return f"https://drive.google.com/drive/folders/{effective_folder_id}"


def get_google_drive_service_account_email() -> Optional[str]:
    info = _load_service_account_info()
    if not info:
        return None
    return info.get("client_email")


def _get_access_token() -> str:
    info = _load_service_account_info()
    if not info:
        raise GoogleDriveBackupError(
            "Credencial do Google Drive nao encontrada. Configure a conta de servico antes de sincronizar."
        )

    try:
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=GOOGLE_DRIVE_SCOPE,
        )
        credentials.refresh(Request())
    except Exception as exc:
        raise GoogleDriveBackupError(
            "Nao foi possivel autenticar no Google Drive com a conta de servico configurada."
        ) from exc

    if not credentials.token:
        raise GoogleDriveBackupError("Nao foi possivel obter token de acesso do Google Drive.")

    return credentials.token


def _safe_query_value(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace("'", "\\'")


def _drive_request(
    method: str,
    url: str,
    *,
    token: str,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    with httpx.Client(timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS) as client:
        response = client.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            files=files,
        )

    if response.status_code >= 400:
        raise GoogleDriveBackupError(
            f"Falha ao sincronizar com Google Drive: {response.text.strip() or response.reason_phrase}"
        )

    if not response.content:
        return {}

    return response.json()


def _find_child_folder(token: str, parent_id: str, name: str) -> Optional[Dict[str, Any]]:
    query = (
        f"trashed=false and mimeType='{GOOGLE_DRIVE_FOLDER_MIME}' and "
        f"name='{_safe_query_value(name)}' and '{parent_id}' in parents"
    )
    data = _drive_request(
        "GET",
        GOOGLE_DRIVE_FILES_URL,
        token=token,
        params={
            "q": query,
            "fields": "files(id,name,webViewLink)",
            "pageSize": 1,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        },
    )
    files = data.get("files") or []
    return files[0] if files else None


def _ensure_folder(token: str, parent_id: str, name: str) -> Dict[str, Any]:
    existing = _find_child_folder(token, parent_id, name)
    if existing:
        existing["webViewLink"] = existing.get("webViewLink") or get_google_drive_folder_url(existing["id"])
        return existing

    created = _drive_request(
        "POST",
        GOOGLE_DRIVE_FILES_URL,
        token=token,
        params={
            "supportsAllDrives": "true",
        },
        json_body={
            "name": name,
            "mimeType": GOOGLE_DRIVE_FOLDER_MIME,
            "parents": [parent_id],
        },
    )
    created["webViewLink"] = created.get("webViewLink") or get_google_drive_folder_url(created.get("id"))
    return created


def _find_child_file(token: str, parent_id: str, name: str) -> Optional[Dict[str, Any]]:
    query = (
        f"trashed=false and name='{_safe_query_value(name)}' and '{parent_id}' in parents"
    )
    data = _drive_request(
        "GET",
        GOOGLE_DRIVE_FILES_URL,
        token=token,
        params={
            "q": query,
            "fields": "files(id,name,webViewLink,webContentLink)",
            "pageSize": 1,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        },
    )
    files = data.get("files") or []
    return files[0] if files else None


def _upload_file(token: str, parent_id: str, file_path: Path) -> Dict[str, Any]:
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    existing = _find_child_file(token, parent_id, file_path.name)
    metadata = {"name": file_path.name, "parents": [parent_id]}
    method = "PATCH" if existing else "POST"
    url = (
        f"{GOOGLE_DRIVE_UPLOAD_URL}/{existing['id']}"
        if existing
        else GOOGLE_DRIVE_UPLOAD_URL
    )

    with file_path.open("rb") as file_handle:
        uploaded = _drive_request(
            method,
            url,
            token=token,
            params={
                "uploadType": "multipart",
                "fields": "id,name,webViewLink,webContentLink",
                "supportsAllDrives": "true",
            },
            files={
                "metadata": (
                    "metadata",
                    json.dumps(metadata),
                    "application/json; charset=UTF-8",
                ),
                "file": (file_path.name, file_handle, mime_type),
            },
        )

    uploaded["webViewLink"] = uploaded.get("webViewLink") or (
        f"https://drive.google.com/file/d/{uploaded.get('id')}/view"
        if uploaded.get("id")
        else None
    )
    return uploaded


def sync_backup_directory(backup_dir: Path) -> Dict[str, Any]:
    if not is_google_drive_enabled():
        raise GoogleDriveBackupError("A sincronizacao com Google Drive esta desabilitada.")

    if not is_google_drive_configured():
        raise GoogleDriveBackupError(
            "Conector do Google Drive ainda nao configurado. Informe a pasta e a conta de servico."
        )

    if not backup_dir.exists() or not backup_dir.is_dir():
        raise GoogleDriveBackupError("Diretorio de backup nao encontrado para sincronizacao.")

    token = _get_access_token()
    root_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID or ""
    root_folder_url = get_google_drive_folder_url(root_folder_id)
    remote_folder = _ensure_folder(token, root_folder_id, backup_dir.name)

    synced_files: Dict[str, Dict[str, Optional[str]]] = {}
    for filename in ("database.sql", "assets.tar.gz", "manifest.txt"):
        candidate = backup_dir / filename
        if not candidate.exists():
            continue
        uploaded = _upload_file(token, remote_folder["id"], candidate)
        synced_files[filename] = {
            "id": uploaded.get("id"),
            "name": uploaded.get("name"),
            "url": uploaded.get("webViewLink") or uploaded.get("webContentLink"),
        }

    return {
        "status": "synced",
        "root_folder_id": root_folder_id,
        "root_folder_url": root_folder_url,
        "backup_folder_id": remote_folder.get("id"),
        "backup_folder_url": remote_folder.get("webViewLink"),
        "service_account_email": get_google_drive_service_account_email(),
        "files": synced_files,
    }
