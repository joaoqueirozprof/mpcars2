import os
import subprocess
from datetime import datetime
from pathlib import Path

from app.celery_app import celery
from app.core.config import settings


@celery.task(name="app.tasks.backup.executar_backup")
def executar_backup():
    """Executa backup do banco de dados via pg_dump."""
    backup_dir = Path(settings.BACKUP_DIRECTORY)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = backup_dir / timestamp
    target_dir.mkdir(parents=True, exist_ok=True)
    db_file = target_dir / "database.sql"

    try:
        from sqlalchemy.engine import make_url
        runtime_url = make_url(settings.database_url_for_runtime)
        env = os.environ.copy()
        if runtime_url.password:
            env["PGPASSWORD"] = runtime_url.password
        result = subprocess.run(
            [
                "pg_dump", "--no-owner", "--no-privileges", "--clean", "--if-exists",
                "-h", runtime_url.host or "localhost",
                "-p", str(runtime_url.port or 5432),
                "-U", runtime_url.username or "postgres",
                "-d", (runtime_url.database or "").lstrip("/"),
            ],
            capture_output=True, text=True, env=env,
            timeout=settings.BACKUP_COMMAND_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            db_file.write_text(result.stdout, encoding="utf-8")
            manifest = target_dir / "manifest.txt"
            manifest.write_text(
                "timestamp={}\nbackup_mode=celery-scheduled\n".format(timestamp),
                encoding="utf-8",
            )
            return "Backup salvo em {}".format(target_dir)
        return "pg_dump falhou: {}".format(result.stderr[:200])
    except FileNotFoundError:
        return "pg_dump nao disponivel no container"
    except subprocess.TimeoutExpired:
        return "Timeout ao gerar backup"
    except Exception as e:
        return "Erro no backup: {}".format(str(e))
