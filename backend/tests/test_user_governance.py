from pathlib import Path


def test_admin_can_create_owner_with_governance_only(client, admin_headers):
    response = client.post(
        "/api/v1/usuarios/",
        headers=admin_headers,
        json={
            "email": "owner@example.org",
            "password": "OwnerSeguro123",
            "nome": "Dono da Empresa",
            "perfil": "owner",
            "permitted_pages": ["clientes", "contratos"],
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["perfil"] == "owner"
    assert body["permitted_pages"] == ["governanca"]


def test_owner_can_access_backups_but_not_clientes(client, user_factory, login_as):
    owner = user_factory(
        email="owner-backup@example.org",
        password="OwnerSeguro123",
        perfil="owner",
        permitted_pages=["governanca"],
    )
    headers = login_as(owner.email, "OwnerSeguro123")

    backups_response = client.get("/api/v1/ops/backups", headers=headers)
    clientes_response = client.get("/api/v1/clientes/", headers=headers)

    assert backups_response.status_code == 200, backups_response.text
    assert clientes_response.status_code == 403, clientes_response.text


def test_generic_admin_cannot_access_governance_panels(client, admin_headers):
    backups_response = client.get("/api/v1/ops/backups", headers=admin_headers)
    readiness_response = client.get("/api/v1/ops/readiness", headers=admin_headers)

    assert backups_response.status_code == 403, backups_response.text
    assert readiness_response.status_code == 403, readiness_response.text


def test_platform_admin_can_run_backup_without_shell_script(
    client,
    platform_admin_headers,
    monkeypatch,
    tmp_path,
):
    from app.core.config import settings
    from app.routers import ops

    backup_root = tmp_path / "backups"

    monkeypatch.setattr(settings, "BACKUP_ENABLED", True)
    monkeypatch.setattr(settings, "BACKUP_DIRECTORY", str(backup_root))
    monkeypatch.setattr(settings, "BACKUP_SCRIPT_PATH", "/ops/arquivo_inexistente.sh")

    def fake_dump(target_file: Path) -> str:
        target_file.write_text("-- dump de teste\n", encoding="utf-8")
        return "Dump de teste criado"

    def fake_assets(target_file: Path) -> str:
        target_file.write_bytes(b"assets")
        return "Assets de teste criados"

    monkeypatch.setattr(ops, "_write_database_dump", fake_dump)
    monkeypatch.setattr(ops, "_write_assets_archive", fake_assets)

    response = client.post("/api/v1/ops/backups/run", headers=platform_admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "backup_executado"
    assert body["latest_backup"] is not None
    assert "Dump de teste criado" in body["output"]
    assert any(item.is_dir() for item in backup_root.iterdir())


def test_admin_generates_recovery_link_and_user_completes_reset(
    client,
    admin_headers,
    user_factory,
):
    user = user_factory(
        email="gerente-reset@example.org",
        password="GerenteAntigo123",
        perfil="gerente",
        permitted_pages=["dashboard", "clientes"],
    )

    reset_response = client.post(
        f"/api/v1/usuarios/{user.id}/reset-senha",
        headers=admin_headers,
        json={},
    )

    assert reset_response.status_code == 200, reset_response.text
    recovery_url = reset_response.json()["recovery_url"]
    token = recovery_url.split("token=")[1]

    validate_response = client.post(
        "/api/v1/auth/password-reset/validate",
        json={"token": token},
    )
    assert validate_response.status_code == 200, validate_response.text

    complete_response = client.post(
        "/api/v1/auth/password-reset/complete",
        json={"token": token, "senha_nova": "NovaSenha123"},
    )
    assert complete_response.status_code == 200, complete_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "NovaSenha123"},
    )
    assert login_response.status_code == 200, login_response.text


def test_admin_can_delete_regular_user(client, admin_headers, user_factory):
    user = user_factory(
        email="operador-excluir@example.org",
        password="OperadorSeguro123",
        perfil="operador",
        permitted_pages=["dashboard", "clientes"],
    )

    delete_response = client.delete(f"/api/v1/usuarios/{user.id}", headers=admin_headers)
    assert delete_response.status_code == 204, delete_response.text

    list_response = client.get("/api/v1/usuarios/", headers=admin_headers)
    assert list_response.status_code == 200, list_response.text
    assert all(item["id"] != user.id for item in list_response.json())


def test_admin_cannot_delete_own_account(client, platform_admin_headers):
    delete_response = client.delete("/api/v1/usuarios/1", headers=platform_admin_headers)
    assert delete_response.status_code == 400, delete_response.text
    assert "propria conta" in delete_response.json()["detail"]
