def test_public_register_disabled(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "novo@example.org",
            "password": "SenhaForte123",
            "nome": "Novo Usuario",
            "perfil": "admin",
        },
    )

    assert response.status_code == 403
    assert "desabilitado" in response.json()["detail"].lower()


def test_non_admin_without_permission_cannot_access_clientes(client, user_factory, login_as):
    user = user_factory(
        email="sem-permissao@example.org",
        password="SenhaForte123",
        permitted_pages=[],
    )
    headers = login_as(user.email, "SenhaForte123")

    response = client.get("/api/v1/clientes/", headers=headers)

    assert response.status_code == 403
    assert "permissao" in response.json()["detail"].lower()


def test_non_admin_with_permission_can_access_clientes(client, user_factory, login_as):
    user = user_factory(
        email="com-permissao@example.org",
        password="SenhaForte123",
        permitted_pages=["clientes"],
    )
    headers = login_as(user.email, "SenhaForte123")

    response = client.get("/api/v1/clientes/", headers=headers)

    assert response.status_code == 200
    assert "data" in response.json()


def test_admin_cannot_create_user_with_weak_password(client, admin_headers):
    response = client.post(
        "/api/v1/usuarios/",
        headers=admin_headers,
        json={
            "email": "fraco@example.org",
            "password": "123",
            "nome": "Senha Fraca",
            "perfil": "user",
            "permitted_pages": ["clientes"],
        },
    )

    assert response.status_code == 400
    assert "senha" in response.json()["detail"].lower()


def test_profile_update_keeps_token_valid_after_email_change(client, admin_headers):
    response = client.put(
        "/api/v1/auth/profile",
        headers=admin_headers,
        json={"nome": "Admin Atualizado", "email": "NOVO.ADMIN@example.org"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "novo.admin@example.org"
    assert body["nome"] == "Admin Atualizado"

    me_response = client.get("/api/v1/auth/me", headers=admin_headers)

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "novo.admin@example.org"
