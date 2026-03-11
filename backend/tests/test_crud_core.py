def test_cliente_crud_with_legacy_aliases(client, admin_headers):
    create_response = client.post(
        "/api/v1/clientes/",
        headers=admin_headers,
        json={
            "nome": "Cliente Teste",
            "cpf_cnpj": "123.456.789-09",
            "telefone": "(11) 99999-1234",
            "email": "cliente.teste@example.org",
            "endereco": "Rua Um",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "cep": "01001-000",
        },
    )

    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert created["cpf"] == "12345678909"
    assert created["endereco_residencial"] == "Rua Um"

    patch_response = client.patch(
        f"/api/v1/clientes/{created['id']}",
        headers=admin_headers,
        json={"cidade": "Campinas", "telefone": "(11) 98888-7777"},
    )

    assert patch_response.status_code == 200, patch_response.text
    patched = patch_response.json()
    assert patched["cidade_residencial"] == "Campinas"
    assert patched["telefone"] == "11988887777"

    delete_response = client.delete(
        f"/api/v1/clientes/{created['id']}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/api/v1/clientes/{created['id']}",
        headers=admin_headers,
    )
    assert get_response.status_code == 404


def test_financeiro_manual_crud(client, admin_headers):
    create_response = client.post(
        "/api/v1/financeiro/",
        headers=admin_headers,
        json={
            "tipo": "despesa",
            "categoria": "Teste",
            "descricao": "Lancamento manual de teste",
            "valor": 123.45,
            "data": "2026-03-11",
            "status": "pendente",
        },
    )

    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["id"].startswith("fm-")

    patch_response = client.patch(
        f"/api/v1/financeiro/{created['id']}",
        headers=admin_headers,
        json={"status": "pago", "valor": 222.22},
    )

    assert patch_response.status_code == 200, patch_response.text
    patched = patch_response.json()
    assert patched["status"] == "pago"
    assert float(patched["valor"]) == 222.22

    list_response = client.get(
        "/api/v1/financeiro/?page=1&limit=50",
        headers=admin_headers,
    )

    assert list_response.status_code == 200
    ids = {item["id"] for item in list_response.json()["data"]}
    assert created["id"] in ids

    delete_response = client.delete(
        f"/api/v1/financeiro/{created['id']}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 204
