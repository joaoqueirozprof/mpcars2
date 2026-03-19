"""
MPCars2 Comprehensive Integration Tests
Tests all critical business flows against SQLite test database.
"""
import pytest


def create_veiculo(client, headers, **kw):
    data = {"placa": kw.get("placa", "TST1A23"), "marca": "FIAT", "modelo": "MOBI", "ano": 2024, "km_atual": kw.get("km_atual", 10000), "status": "disponivel"}
    data.update(kw)
    r = client.post("/api/v1/veiculos/", json=data, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def create_cliente(client, headers, **kw):
    data = {"nome": kw.get("nome", "Cliente Teste"), "cpf": kw.get("cpf", "12345678901"), "telefone": "11999999999", "ativo": True}
    data.update(kw)
    r = client.post("/api/v1/clientes/", json=data, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


class TestAuth:
    def test_login_success(self, client, admin_user):
        r = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "AdminSeguro123"})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, client, admin_user):
        r = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "Errada"})
        assert r.status_code == 401

    def test_me_authenticated(self, client, admin_headers):
        assert client.get("/api/v1/auth/me", headers=admin_headers).status_code == 200

    def test_me_unauthenticated(self, client):
        assert client.get("/api/v1/auth/me").status_code in (401, 403)


class TestVeiculos:
    def test_create_and_list(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        assert v["placa"] == "TST1A23"
        assert client.get("/api/v1/veiculos/", headers=admin_headers).status_code == 200

    def test_duplicate_placa(self, client, admin_headers):
        create_veiculo(client, admin_headers, placa="DUP1A23")
        r = client.post("/api/v1/veiculos/", json={"placa": "DUP1A23", "marca": "X", "modelo": "Y"}, headers=admin_headers)
        assert r.status_code == 400

    def test_update_and_delete(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        assert client.patch(f"/api/v1/veiculos/{v['id']}", json={"cor": "Preto"}, headers=admin_headers).status_code == 200
        assert client.delete(f"/api/v1/veiculos/{v['id']}", headers=admin_headers).status_code == 204


class TestClientes:
    def test_duplicate_cpf(self, client, admin_headers):
        create_cliente(client, admin_headers, cpf="99988877766")
        r = client.post("/api/v1/clientes/", json={"nome": "Outro", "cpf": "99988877766"}, headers=admin_headers)
        assert r.status_code == 400

    def test_update_and_delete(self, client, admin_headers):
        c = create_cliente(client, admin_headers)
        assert client.patch(f"/api/v1/clientes/{c['id']}", json={"nome": "Novo"}, headers=admin_headers).status_code == 200
        assert client.delete(f"/api/v1/clientes/{c['id']}", headers=admin_headers).status_code == 204


class TestContratos:
    def test_create_marks_vehicle_rented(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c = create_cliente(client, admin_headers)
        r = client.post("/api/v1/contratos/", json={"cliente_id": c["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": 100.0}, headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "ativo"
        assert client.get(f"/api/v1/veiculos/{v['id']}", headers=admin_headers).json()["status"] == "alugado"

    def test_negative_valor_rejected(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c = create_cliente(client, admin_headers)
        r = client.post("/api/v1/contratos/", json={"cliente_id": c["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": -50.0}, headers=admin_headers)
        assert r.status_code == 400

    def test_finalize_frees_vehicle(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c = create_cliente(client, admin_headers)
        rc = client.post("/api/v1/contratos/", json={"cliente_id": c["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": 100.0}, headers=admin_headers)
        ct = rc.json()
        rf = client.post(f"/api/v1/contratos/{ct['id']}/encerrar", json={"km_atual_veiculo": 10500, "status_pagamento": "pago"}, headers=admin_headers)
        assert rf.status_code == 200
        assert rf.json()["status"] == "finalizado"
        assert client.get(f"/api/v1/veiculos/{v['id']}", headers=admin_headers).json()["status"] == "disponivel"

    def test_cannot_double_book(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c1 = create_cliente(client, admin_headers, cpf="11111111111")
        c2 = create_cliente(client, admin_headers, cpf="22222222222")
        client.post("/api/v1/contratos/", json={"cliente_id": c1["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": 100.0}, headers=admin_headers)
        r2 = client.post("/api/v1/contratos/", json={"cliente_id": c2["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": 100.0}, headers=admin_headers)
        assert r2.status_code == 400

    def test_delete_frees_vehicle(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c = create_cliente(client, admin_headers)
        rc = client.post("/api/v1/contratos/", json={"cliente_id": c["id"], "veiculo_id": v["id"], "data_inicio": "2026-03-20", "data_fim": "2026-03-25", "valor_diaria": 100.0}, headers=admin_headers)
        client.delete(f"/api/v1/contratos/{rc.json()['id']}", headers=admin_headers)
        assert client.get(f"/api/v1/veiculos/{v['id']}", headers=admin_headers).json()["status"] == "disponivel"


class TestMultas:
    def test_crud_and_double_payment(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        r = client.post("/api/v1/multas/", json={"veiculo_id": v["id"], "valor": 200.0, "data_vencimento": "2026-04-01"}, headers=admin_headers)
        assert r.status_code == 200
        m = r.json()
        assert client.post(f"/api/v1/multas/{m['id']}/pagar", headers=admin_headers).json()["status"] == "pago"
        assert client.post(f"/api/v1/multas/{m['id']}/pagar", headers=admin_headers).status_code == 400

    def test_resumo(self, client, admin_headers):
        assert client.get("/api/v1/multas/resumo", headers=admin_headers).status_code == 200


class TestDespesasLoja:
    def test_crud(self, client, admin_headers):
        r = client.post("/api/v1/despesas-loja/", json={"categoria": "Aluguel", "descricao": "Mensal", "valor": 3000.0, "mes": 3, "ano": 2026}, headers=admin_headers)
        assert r.status_code == 201
        d = r.json()
        assert client.patch(f"/api/v1/despesas-loja/{d['id']}", json={"valor": 3500.0}, headers=admin_headers).status_code == 200
        client.delete(f"/api/v1/despesas-loja/{d['id']}", headers=admin_headers)

    def test_invalid_month(self, client, admin_headers):
        r = client.post("/api/v1/despesas-loja/", json={"categoria": "X", "descricao": "X", "valor": 100.0, "mes": 13, "ano": 2026}, headers=admin_headers)
        assert r.status_code == 400


class TestDashboard:
    def test_all_endpoints(self, client, admin_headers):
        assert client.get("/api/v1/dashboard/", headers=admin_headers).status_code == 200
        assert client.get("/api/v1/dashboard/graficos", headers=admin_headers).status_code == 200
        assert client.get("/api/v1/dashboard/metricas", headers=admin_headers).status_code == 200


class TestFinanceiro:
    def test_list_and_resumo(self, client, admin_headers):
        assert client.get("/api/v1/financeiro/", headers=admin_headers).status_code == 200
        assert client.get("/api/v1/financeiro/resumo", headers=admin_headers).status_code == 200

    def test_faturamento_invalid_month(self, client, admin_headers):
        assert client.get("/api/v1/financeiro/faturamento?mes=13&ano=2026", headers=admin_headers).status_code == 422


class TestManutencoes:
    def test_complete_blocks_reopen(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        r = client.post("/api/v1/manutencoes/", json={"veiculo_id": v["id"], "tipo": "preventiva", "descricao": "Oleo", "status": "pendente"}, headers=admin_headers)
        m = r.json()
        client.post(f"/api/v1/manutencoes/{m['id']}/completar", headers=admin_headers)
        assert client.patch(f"/api/v1/manutencoes/{m['id']}", json={"status": "pendente"}, headers=admin_headers).status_code == 400


class TestReservas:
    def test_create_sets_reserved(self, client, admin_headers):
        v = create_veiculo(client, admin_headers)
        c = create_cliente(client, admin_headers)
        client.post("/api/v1/reservas/", json={"cliente_id": c["id"], "veiculo_id": v["id"], "data_inicio": "2026-04-01T00:00:00", "data_fim": "2026-04-05T00:00:00"}, headers=admin_headers)
        assert client.get(f"/api/v1/veiculos/{v['id']}", headers=admin_headers).json()["status"] == "reservado"


class TestPagination:
    def test_edge_cases(self, client, admin_headers):
        assert client.get("/api/v1/veiculos/?page=0", headers=admin_headers).status_code == 200
        assert client.get("/api/v1/veiculos/?page=999", headers=admin_headers).status_code == 200
