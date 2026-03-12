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
