import base64
import hashlib
import json
import mimetypes
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

import httpx
from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Configuracao


GOOGLE_DRIVE_SCOPE = ["https://www.googleapis.com/auth/drive"]
GOOGLE_DRIVE_OAUTH_SCOPE = "https://www.googleapis.com/auth/drive.file openid email profile"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_OAUTH_DEVICE_URL = "https://oauth2.googleapis.com/device/code"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_OAUTH_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_OAUTH_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

CONFIG_AUTH_MODE = "google_drive_auth_mode"
CONFIG_ENABLED = "google_drive_enabled"
CONFIG_SYNC_ON_BACKUP = "google_drive_sync_on_backup"
CONFIG_OAUTH_CLIENT_ID = "google_drive_oauth_client_id"
CONFIG_OAUTH_CLIENT_SECRET = "google_drive_oauth_client_secret"
CONFIG_OAUTH_REFRESH_TOKEN = "google_drive_oauth_refresh_token"
CONFIG_OAUTH_CONNECTED_EMAIL = "google_drive_oauth_connected_email"
CONFIG_OAUTH_ROOT_FOLDER_ID = "google_drive_oauth_root_folder_id"
CONFIG_OAUTH_ROOT_FOLDER_NAME = "google_drive_oauth_root_folder_name"
CONFIG_OAUTH_DEVICE_CODE = "google_drive_oauth_device_code"
CONFIG_OAUTH_USER_CODE = "google_drive_oauth_user_code"
CONFIG_OAUTH_VERIFICATION_URL = "google_drive_oauth_verification_url"
CONFIG_OAUTH_EXPIRES_AT = "google_drive_oauth_expires_at"
CONFIG_OAUTH_INTERVAL_SECONDS = "google_drive_oauth_interval_seconds"
CONFIG_OAUTH_CONNECTED_AT = "google_drive_oauth_connected_at"

ENCRYPTED_PREFIX = "enc::"
DEFAULT_OAUTH_ROOT_FOLDER_NAME = "MPCARS Backups"
ALL_GOOGLE_CONFIG_KEYS = [
    CONFIG_AUTH_MODE,
    CONFIG_ENABLED,
    CONFIG_SYNC_ON_BACKUP,
    CONFIG_OAUTH_CLIENT_ID,
    CONFIG_OAUTH_CLIENT_SECRET,
    CONFIG_OAUTH_REFRESH_TOKEN,
    CONFIG_OAUTH_CONNECTED_EMAIL,
    CONFIG_OAUTH_ROOT_FOLDER_ID,
    CONFIG_OAUTH_ROOT_FOLDER_NAME,
    CONFIG_OAUTH_DEVICE_CODE,
    CONFIG_OAUTH_USER_CODE,
    CONFIG_OAUTH_VERIFICATION_URL,
    CONFIG_OAUTH_EXPIRES_AT,
    CONFIG_OAUTH_INTERVAL_SECONDS,
    CONFIG_OAUTH_CONNECTED_AT,
]


class GoogleDriveBackupError(RuntimeError):
    pass


def _fernet() -> Fernet:
    source = (settings.SECRET_KEY or "mpcars2-google-drive").encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(source).digest())
    return Fernet(key)


def _encrypt_secret(value: Optional[str]) -> Optional[str]:
    normalized = (value or "").strip()
    if not normalized:
        return None
    return ENCRYPTED_PREFIX + _fernet().encrypt(normalized.encode("utf-8")).decode("utf-8")


def _decrypt_secret(value: Optional[str]) -> Optional[str]:
    normalized = (value or "").strip()
    if not normalized:
        return None
    if not normalized.startswith(ENCRYPTED_PREFIX):
        return normalized
    try:
        payload = normalized[len(ENCRYPTED_PREFIX) :].encode("utf-8")
        return _fernet().decrypt(payload).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


@contextmanager
def _session_scope(db: Optional[Session] = None) -> Iterator[Tuple[Session, bool]]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


def _load_config_map(session: Session) -> Dict[str, str]:
    rows = session.query(Configuracao).filter(Configuracao.chave.in_(ALL_GOOGLE_CONFIG_KEYS)).all()
    return {row.chave: row.valor or "" for row in rows}


def _save_config_values(
    session: Session,
    updates: Dict[str, Optional[str]],
    *,
    remove_keys: Optional[list[str]] = None,
) -> None:
    keys = list(updates.keys()) + list(remove_keys or [])
    existing = {
        row.chave: row
        for row in session.query(Configuracao).filter(Configuracao.chave.in_(keys)).all()
    }

    for key in remove_keys or []:
        row = existing.get(key)
        if row is not None:
            session.delete(row)

    for key, value in updates.items():
        if value is None:
            row = existing.get(key)
            if row is not None:
                session.delete(row)
            continue

        serialized = str(value)
        row = existing.get(key)
        if row is None:
            session.add(Configuracao(chave=key, valor=serialized))
        else:
            row.valor = serialized

    session.commit()


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


def _safe_query_value(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace("'", "\\'")


def _google_json_request(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
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
            data=data,
        )

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason_phrase
        raise GoogleDriveBackupError(f"Falha ao sincronizar com Google Drive: {detail}")

    if not response.content:
        return {}

    return response.json()


def _oauth_form_request(url: str, payload: Dict[str, str]) -> Dict[str, Any]:
    with httpx.Client(timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS) as client:
        response = client.post(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text.strip() or response.reason_phrase
        raise GoogleDriveBackupError(f"Falha ao falar com o Google OAuth: {detail}")

    return response.json()


def _fetch_google_user_email(token: str) -> Optional[str]:
    try:
        data = _google_json_request("GET", GOOGLE_OAUTH_USERINFO_URL, token=token)
    except GoogleDriveBackupError:
        return None
    return data.get("email")


def _find_child_folder(token: str, parent_id: str, name: str) -> Optional[Dict[str, Any]]:
    query = (
        f"trashed=false and mimeType='{GOOGLE_DRIVE_FOLDER_MIME}' and "
        f"name='{_safe_query_value(name)}' and '{parent_id}' in parents"
    )
    data = _google_json_request(
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
        existing["webViewLink"] = existing.get("webViewLink") or get_google_drive_folder_url(existing.get("id"))
        return existing

    created = _google_json_request(
        "POST",
        GOOGLE_DRIVE_FILES_URL,
        token=token,
        params={"supportsAllDrives": "true"},
        json_body={
            "name": name,
            "mimeType": GOOGLE_DRIVE_FOLDER_MIME,
            "parents": [parent_id],
        },
    )
    created["webViewLink"] = created.get("webViewLink") or get_google_drive_folder_url(created.get("id"))
    return created


def _find_child_file(token: str, parent_id: str, name: str) -> Optional[Dict[str, Any]]:
    query = f"trashed=false and name='{_safe_query_value(name)}' and '{parent_id}' in parents"
    data = _google_json_request(
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
    url = f"{GOOGLE_DRIVE_UPLOAD_URL}/{existing['id']}" if existing else GOOGLE_DRIVE_UPLOAD_URL

    with file_path.open("rb") as file_handle:
        uploaded = _google_json_request(
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
        f"https://drive.google.com/file/d/{uploaded.get('id')}/view" if uploaded.get("id") else None
    )
    return uploaded


def _service_account_access_token() -> str:
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


def _build_state(config: Dict[str, str]) -> Dict[str, Any]:
    oauth_client_id = (config.get(CONFIG_OAUTH_CLIENT_ID) or "").strip()
    oauth_client_secret = _decrypt_secret(config.get(CONFIG_OAUTH_CLIENT_SECRET))
    oauth_refresh_token = _decrypt_secret(config.get(CONFIG_OAUTH_REFRESH_TOKEN))
    oauth_connected_email = (config.get(CONFIG_OAUTH_CONNECTED_EMAIL) or "").strip() or None
    oauth_root_folder_id = (config.get(CONFIG_OAUTH_ROOT_FOLDER_ID) or "").strip() or None
    oauth_root_folder_name = (config.get(CONFIG_OAUTH_ROOT_FOLDER_NAME) or "").strip() or DEFAULT_OAUTH_ROOT_FOLDER_NAME
    pending_device_code = _decrypt_secret(config.get(CONFIG_OAUTH_DEVICE_CODE))
    pending_user_code = (config.get(CONFIG_OAUTH_USER_CODE) or "").strip() or None
    pending_verification_url = (config.get(CONFIG_OAUTH_VERIFICATION_URL) or "").strip() or None
    pending_interval_seconds = int((config.get(CONFIG_OAUTH_INTERVAL_SECONDS) or "5").strip() or "5")
    pending_expires_at_raw = (config.get(CONFIG_OAUTH_EXPIRES_AT) or "").strip() or None
    pending_expires_at = None
    if pending_expires_at_raw:
        try:
            pending_expires_at = datetime.fromisoformat(pending_expires_at_raw)
        except ValueError:
            pending_expires_at = None

    pending_active = bool(
        pending_device_code
        and pending_user_code
        and pending_verification_url
        and pending_expires_at
        and pending_expires_at > datetime.now(timezone.utc)
    )

    service_account_info = _load_service_account_info()
    service_account_email = service_account_info.get("client_email") if service_account_info else None

    requested_auth_mode = (config.get(CONFIG_AUTH_MODE) or "").strip().lower()
    has_oauth_state = any(
        [
            requested_auth_mode == "oauth",
            oauth_client_id,
            oauth_client_secret,
            oauth_refresh_token,
            pending_active,
        ]
    )

    if has_oauth_state:
        auth_mode = "oauth"
        enabled = _parse_bool(config.get(CONFIG_ENABLED))
        if enabled is None:
            enabled = True
        sync_on_backup = _parse_bool(config.get(CONFIG_SYNC_ON_BACKUP))
        if sync_on_backup is None:
            sync_on_backup = True
        configured = bool(enabled and oauth_client_id and oauth_client_secret and oauth_refresh_token)
        folder_id = oauth_root_folder_id
        folder_url = get_google_drive_folder_url(folder_id)
        account_email = oauth_connected_email
    elif settings.GOOGLE_DRIVE_BACKUP_ENABLED and settings.GOOGLE_DRIVE_FOLDER_ID and service_account_info:
        auth_mode = "service_account"
        enabled = True
        sync_on_backup = settings.GOOGLE_DRIVE_SYNC_ON_BACKUP
        configured = True
        folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        folder_url = get_google_drive_folder_url(folder_id)
        account_email = service_account_email
    else:
        auth_mode = "none"
        enabled = False
        sync_on_backup = False
        configured = False
        folder_id = None
        folder_url = None
        account_email = None

    return {
        "auth_mode": auth_mode,
        "enabled": enabled,
        "configured": configured,
        "sync_on_backup": sync_on_backup,
        "folder_id": folder_id,
        "folder_url": folder_url,
        "folder_name": oauth_root_folder_name,
        "account_email": account_email,
        "service_account_email": service_account_email,
        "oauth_client_id": oauth_client_id or None,
        "oauth_client_secret": oauth_client_secret,
        "oauth_refresh_token": oauth_refresh_token,
        "pending_device_code": pending_device_code,
        "pending_authorization": {
            "pending": pending_active,
            "user_code": pending_user_code if pending_active else None,
            "verification_url": pending_verification_url if pending_active else None,
            "expires_at": pending_expires_at.isoformat() if pending_active and pending_expires_at else None,
            "interval_seconds": pending_interval_seconds if pending_active else None,
        },
    }


def _load_state(db: Optional[Session] = None) -> Dict[str, Any]:
    with _session_scope(db) as (session, _):
        config = _load_config_map(session)
    return _build_state(config)


def get_google_drive_folder_url(folder_id: Optional[str] = None) -> Optional[str]:
    effective_folder_id = (folder_id or "").strip()
    if not effective_folder_id:
        return None
    return f"https://drive.google.com/drive/folders/{effective_folder_id}"


def get_google_drive_service_account_email() -> Optional[str]:
    info = _load_service_account_info()
    if not info:
        return None
    return info.get("client_email")


def get_google_drive_overview(db: Optional[Session] = None) -> Dict[str, Any]:
    state = _load_state(db)
    return {
        "enabled": state["enabled"],
        "configured": state["configured"],
        "sync_on_backup": state["sync_on_backup"],
        "auth_mode": state["auth_mode"],
        "folder_id": state["folder_id"],
        "folder_url": state["folder_url"],
        "folder_name": state["folder_name"],
        "account_email": state["account_email"],
        "service_account_email": state["service_account_email"],
        "client_id_configured": bool(state["oauth_client_id"]),
        "pending_authorization": state["pending_authorization"],
    }


def is_google_drive_enabled(db: Optional[Session] = None) -> bool:
    return bool(_load_state(db)["enabled"])


def is_google_drive_configured(db: Optional[Session] = None) -> bool:
    return bool(_load_state(db)["configured"])


def is_google_drive_sync_on_backup(db: Optional[Session] = None) -> bool:
    state = _load_state(db)
    return bool(state["enabled"] and state["sync_on_backup"])


def get_google_drive_account_email(db: Optional[Session] = None) -> Optional[str]:
    return _load_state(db).get("account_email")


def start_google_drive_device_authorization(
    client_id: str,
    client_secret: str,
    *,
    folder_name: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    normalized_client_id = (client_id or "").strip()
    normalized_client_secret = (client_secret or "").strip()
    normalized_folder_name = (folder_name or "").strip() or DEFAULT_OAUTH_ROOT_FOLDER_NAME

    if not normalized_client_id:
        raise GoogleDriveBackupError("Informe o Client ID do Google OAuth.")
    if not normalized_client_secret:
        raise GoogleDriveBackupError("Informe o Client Secret do Google OAuth.")

    payload = _oauth_form_request(
        GOOGLE_OAUTH_DEVICE_URL,
        {
            "client_id": normalized_client_id,
            "scope": GOOGLE_DRIVE_OAUTH_SCOPE,
        },
    )
    verification_url = payload.get("verification_url") or payload.get("verification_uri")
    user_code = payload.get("user_code")
    device_code = payload.get("device_code")
    expires_in = int(payload.get("expires_in") or 0)
    interval_seconds = int(payload.get("interval") or 5)

    if not verification_url or not user_code or not device_code or expires_in <= 0:
        raise GoogleDriveBackupError("O Google OAuth nao devolveu um codigo valido para a conexao.")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    with _session_scope(db) as (session, _):
        _save_config_values(
            session,
            {
                CONFIG_AUTH_MODE: "oauth",
                CONFIG_ENABLED: "true",
                CONFIG_SYNC_ON_BACKUP: "true",
                CONFIG_OAUTH_CLIENT_ID: normalized_client_id,
                CONFIG_OAUTH_CLIENT_SECRET: _encrypt_secret(normalized_client_secret),
                CONFIG_OAUTH_ROOT_FOLDER_NAME: normalized_folder_name,
                CONFIG_OAUTH_DEVICE_CODE: _encrypt_secret(device_code),
                CONFIG_OAUTH_USER_CODE: user_code,
                CONFIG_OAUTH_VERIFICATION_URL: verification_url,
                CONFIG_OAUTH_EXPIRES_AT: expires_at.isoformat(),
                CONFIG_OAUTH_INTERVAL_SECONDS: str(interval_seconds),
            },
        )

    return {
        "status": "authorization_pending",
        "message": "Abra o Google, informe o codigo e depois conclua a conexao aqui.",
        "user_code": user_code,
        "verification_url": verification_url,
        "expires_at": expires_at.isoformat(),
        "interval_seconds": interval_seconds,
        "folder_name": normalized_folder_name,
    }


def poll_google_drive_device_authorization(db: Optional[Session] = None) -> Dict[str, Any]:
    state = _load_state(db)
    pending = state["pending_authorization"]
    if state["auth_mode"] != "oauth" or not pending.get("pending"):
        raise GoogleDriveBackupError("Nenhuma autorizacao pendente do Google Drive foi encontrada.")

    client_id = state.get("oauth_client_id")
    client_secret = state.get("oauth_client_secret")
    device_code = state.get("pending_device_code")
    if not client_id or not client_secret or not device_code:
        raise GoogleDriveBackupError("Configuracao OAuth incompleta. Gere um novo codigo de conexao.")

    with httpx.Client(timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS) as client:
        response = client.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = {"error": "unknown_error", "error_description": response.text.strip()}

        error_code = detail.get("error")
        if error_code == "authorization_pending":
            return {
                "status": "authorization_pending",
                "message": "Aguardando a autorizacao da conta Google pelo codigo exibido.",
                "pending_authorization": pending,
            }
        if error_code == "slow_down":
            interval_seconds = int((pending.get("interval_seconds") or 5)) + 5
            with _session_scope(db) as (session, _):
                _save_config_values(session, {CONFIG_OAUTH_INTERVAL_SECONDS: str(interval_seconds)})
            pending["interval_seconds"] = interval_seconds
            return {
                "status": "authorization_pending",
                "message": "O Google pediu um intervalo maior antes da proxima checagem.",
                "pending_authorization": pending,
            }

        if error_code in {"expired_token", "access_denied"}:
            with _session_scope(db) as (session, _):
                _save_config_values(
                    session,
                    {},
                    remove_keys=[
                        CONFIG_OAUTH_DEVICE_CODE,
                        CONFIG_OAUTH_USER_CODE,
                        CONFIG_OAUTH_VERIFICATION_URL,
                        CONFIG_OAUTH_EXPIRES_AT,
                        CONFIG_OAUTH_INTERVAL_SECONDS,
                    ],
                )
            message = (
                "A autorizacao expirou. Gere um novo codigo no painel."
                if error_code == "expired_token"
                else "A autorizacao foi negada na conta Google."
            )
            raise GoogleDriveBackupError(message)

        raise GoogleDriveBackupError(
            detail.get("error_description")
            or detail.get("error")
            or "Nao foi possivel concluir a autorizacao do Google Drive."
        )

    payload = response.json()
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token") or state.get("oauth_refresh_token")
    if not access_token:
        raise GoogleDriveBackupError("O Google nao devolveu token de acesso para concluir a conexao.")
    if not refresh_token:
        raise GoogleDriveBackupError(
            "O Google nao devolveu refresh token. Remova a conexao e autorize novamente."
        )

    connected_email = _fetch_google_user_email(access_token)
    root_folder = _ensure_folder(access_token, "root", state["folder_name"])
    connected_at = datetime.now(timezone.utc).isoformat()

    with _session_scope(db) as (session, _):
        _save_config_values(
            session,
            {
                CONFIG_AUTH_MODE: "oauth",
                CONFIG_ENABLED: "true",
                CONFIG_SYNC_ON_BACKUP: "true",
                CONFIG_OAUTH_REFRESH_TOKEN: _encrypt_secret(refresh_token),
                CONFIG_OAUTH_CONNECTED_EMAIL: connected_email,
                CONFIG_OAUTH_ROOT_FOLDER_ID: root_folder.get("id"),
                CONFIG_OAUTH_ROOT_FOLDER_NAME: state["folder_name"],
                CONFIG_OAUTH_CONNECTED_AT: connected_at,
            },
            remove_keys=[
                CONFIG_OAUTH_DEVICE_CODE,
                CONFIG_OAUTH_USER_CODE,
                CONFIG_OAUTH_VERIFICATION_URL,
                CONFIG_OAUTH_EXPIRES_AT,
                CONFIG_OAUTH_INTERVAL_SECONDS,
            ],
        )

    return {
        "status": "connected",
        "message": "Google Drive conectado com sucesso.",
        "account_email": connected_email,
        "folder_id": root_folder.get("id"),
        "folder_url": root_folder.get("webViewLink"),
        "connected_at": connected_at,
        "auth_mode": "oauth",
    }


def disconnect_google_drive_oauth(db: Optional[Session] = None) -> Dict[str, Any]:
    state = _load_state(db)
    refresh_token = state.get("oauth_refresh_token")

    if refresh_token:
        try:
            with httpx.Client(timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS) as client:
                client.post(
                    GOOGLE_OAUTH_REVOKE_URL,
                    data={"token": refresh_token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        except httpx.HTTPError:
            pass

    with _session_scope(db) as (session, _):
        _save_config_values(
            session,
            {
                CONFIG_ENABLED: "false",
            },
            remove_keys=[
                CONFIG_AUTH_MODE,
                CONFIG_OAUTH_REFRESH_TOKEN,
                CONFIG_OAUTH_CONNECTED_EMAIL,
                CONFIG_OAUTH_ROOT_FOLDER_ID,
                CONFIG_OAUTH_DEVICE_CODE,
                CONFIG_OAUTH_USER_CODE,
                CONFIG_OAUTH_VERIFICATION_URL,
                CONFIG_OAUTH_EXPIRES_AT,
                CONFIG_OAUTH_INTERVAL_SECONDS,
                CONFIG_OAUTH_CONNECTED_AT,
            ],
        )

    return {
        "status": "disconnected",
        "message": "Conexao do Google Drive removida com sucesso.",
    }


def _oauth_refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    payload = _oauth_form_request(
        GOOGLE_OAUTH_TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    token = payload.get("access_token")
    if not token:
        raise GoogleDriveBackupError("Nao foi possivel renovar o acesso do Google Drive.")
    return token


def sync_backup_directory(backup_dir: Path, db: Optional[Session] = None) -> Dict[str, Any]:
    state = _load_state(db)
    if not state["enabled"]:
        raise GoogleDriveBackupError("A sincronizacao com Google Drive esta desabilitada.")
    if not state["configured"]:
        raise GoogleDriveBackupError(
            "Conector do Google Drive ainda nao configurado. Conclua a conexao da conta antes de sincronizar."
        )
    if not backup_dir.exists() or not backup_dir.is_dir():
        raise GoogleDriveBackupError("Diretorio de backup nao encontrado para sincronizacao.")

    if state["auth_mode"] == "oauth":
        token = _oauth_refresh_access_token(
            state["oauth_client_id"],
            state["oauth_client_secret"],
            state["oauth_refresh_token"],
        )
        root_folder_id = state["folder_id"] or "root"
        root_folder = (
            {"id": root_folder_id, "webViewLink": state["folder_url"]}
            if state["folder_id"]
            else _ensure_folder(token, "root", state["folder_name"])
        )
        if not state["folder_id"] and root_folder.get("id"):
            with _session_scope(db) as (session, _):
                _save_config_values(
                    session,
                    {
                        CONFIG_OAUTH_ROOT_FOLDER_ID: root_folder.get("id"),
                        CONFIG_OAUTH_ROOT_FOLDER_NAME: state["folder_name"],
                    },
                )
        account_email = state.get("account_email") or _fetch_google_user_email(token)
    else:
        token = _service_account_access_token()
        root_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID or ""
        root_folder = {
            "id": root_folder_id,
            "webViewLink": get_google_drive_folder_url(root_folder_id),
        }
        account_email = get_google_drive_service_account_email()

    remote_folder = _ensure_folder(token, root_folder["id"], backup_dir.name)

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
        "auth_mode": state["auth_mode"],
        "root_folder_id": root_folder.get("id"),
        "root_folder_url": root_folder.get("webViewLink") or get_google_drive_folder_url(root_folder.get("id")),
        "backup_folder_id": remote_folder.get("id"),
        "backup_folder_url": remote_folder.get("webViewLink"),
        "account_email": account_email,
        "service_account_email": get_google_drive_service_account_email() if state["auth_mode"] == "service_account" else None,
        "files": synced_files,
    }
