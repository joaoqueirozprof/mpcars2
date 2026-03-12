from datetime import datetime, timedelta

from app.models import CheckinCheckout, Cliente, Contrato, Reserva, Veiculo


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


def test_contrato_uses_vehicle_km_and_can_be_closed(client, admin_headers, db_session):
    cliente = Cliente(
        nome="Locacao Teste",
        cpf="12345678909",
        email="locacao@example.org",
        telefone="11999990000",
        ativo=True,
    )
    veiculo = Veiculo(
        placa="ABC1234",
        marca="Fiat",
        modelo="Mobi",
        km_atual=15320,
        status="disponivel",
        ativo=True,
    )
    db_session.add_all([cliente, veiculo])
    db_session.commit()
    db_session.refresh(cliente)
    db_session.refresh(veiculo)

    create_response = client.post(
        "/api/v1/contratos/",
        headers=admin_headers,
        json={
            "cliente_id": cliente.id,
            "veiculo_id": veiculo.id,
            "data_inicio": "2026-03-10T10:00:00",
            "data_fim": "2026-03-13T10:00:00",
            "valor_diaria": 100,
            "km_livres": 100,
            "valor_km_excedente": 2.5,
            "combustivel_saida": "Cheio",
        },
    )

    assert create_response.status_code == 200, create_response.text
    contrato_id = create_response.json()["id"]

    db_session.expire_all()
    contrato = db_session.query(Contrato).filter(Contrato.id == contrato_id).first()
    assert contrato is not None
    assert float(contrato.km_inicial) == 15320
    assert contrato.status == "ativo"

    close_response = client.post(
        f"/api/v1/contratos/{contrato_id}/encerrar",
        headers=admin_headers,
        json={
            "km_atual_veiculo": 15480,
            "combustivel_retorno": "3/4",
            "itens_checklist": {
                "estepe": True,
                "triangulo": False,
                "documento": True,
            },
            "valor_avarias": 50,
            "taxa_combustivel": 40,
            "taxa_limpeza": 25,
            "taxa_acessorios": 15,
            "taxa_administrativa": 10,
            "desconto": 20,
            "observacoes": "Risco leve no para-choque",
        },
    )

    assert close_response.status_code == 200, close_response.text

    db_session.expire_all()
    contrato = db_session.query(Contrato).filter(Contrato.id == contrato_id).first()
    veiculo = db_session.query(Veiculo).filter(Veiculo.id == veiculo.id).first()
    checkins = db_session.query(CheckinCheckout).filter(CheckinCheckout.contrato_id == contrato_id).all()

    assert contrato.status == "finalizado"
    assert float(contrato.km_final) == 15480
    assert float(contrato.valor_total) == 570.0
    assert contrato.combustivel_retorno == "3/4"
    assert float(contrato.taxa_combustivel) == 40.0
    assert float(contrato.taxa_limpeza) == 25.0
    assert float(contrato.taxa_acessorios) == 15.0
    assert float(contrato.taxa_administrativa) == 10.0
    assert float(veiculo.km_atual) == 15480
    assert veiculo.status == "disponivel"
    assert len(checkins) == 2
    devolucao = next(checkin for checkin in checkins if checkin.tipo == "devolucao")
    assert devolucao.itens_checklist["triangulo"] is False


def test_dashboard_root_returns_operational_data(client, admin_headers, db_session):
    cliente = Cliente(
        nome="Dashboard Cliente",
        cpf="98765432100",
        email="dashboard@example.org",
        telefone="11999990001",
        ativo=True,
    )
    veiculo_ativo = Veiculo(
        placa="XYZ9876",
        marca="VW",
        modelo="Gol",
        km_atual=22000,
        status="alugado",
        ativo=True,
    )
    veiculo_livre = Veiculo(
        placa="QWE4321",
        marca="Chevrolet",
        modelo="Onix",
        km_atual=8000,
        status="disponivel",
        ativo=True,
    )
    db_session.add_all([cliente, veiculo_ativo, veiculo_livre])
    db_session.commit()
    db_session.refresh(cliente)
    db_session.refresh(veiculo_ativo)

    contrato = Contrato(
        numero="CTR-DASH-1",
        cliente_id=cliente.id,
        veiculo_id=veiculo_ativo.id,
        data_inicio=datetime.now() - timedelta(days=5),
        data_fim=datetime.now() - timedelta(days=1),
        km_inicial=22000,
        valor_diaria=150,
        valor_total=750,
        status="ativo",
        qtd_diarias=5,
        tipo="cliente",
    )
    db_session.add(contrato)
    db_session.commit()

    response = client.get("/api/v1/dashboard/", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_veiculos"] == 2
    assert body["veiculos_alugados"] == 1
    assert body["veiculos_disponiveis"] == 1
    assert body["contratos_ativos"] == 1
    assert body["total_clientes"] == 1
    assert len(body["receita_vs_despesas"]) == 6
    assert body["top_clientes"][0]["nome"] == "Dashboard Cliente"
    assert body["top_veiculos"][0]["placa"] == "XYZ9876"
    assert len(body["contratos_atrasados"]) == 1
    assert len(body["alertas"]) >= 1


def test_reserva_can_be_confirmed_and_converted_to_contract(client, admin_headers, db_session):
    cliente = Cliente(
        nome="Reserva Cliente",
        cpf="22233344455",
        email="reserva@example.org",
        telefone="11999990002",
        ativo=True,
    )
    veiculo = Veiculo(
        placa="RES4321",
        marca="Renault",
        modelo="Kwid",
        km_atual=8120,
        status="disponivel",
        ativo=True,
    )
    db_session.add_all([cliente, veiculo])
    db_session.commit()
    db_session.refresh(cliente)
    db_session.refresh(veiculo)

    create_response = client.post(
        "/api/v1/reservas/",
        headers=admin_headers,
        json={
            "cliente_id": cliente.id,
            "veiculo_id": veiculo.id,
            "data_inicio": "2026-03-15T09:00:00",
            "data_fim": "2026-03-18T09:00:00",
            "valor_estimado": 540,
        },
    )

    assert create_response.status_code == 200, create_response.text
    reserva_id = create_response.json()["id"]

    confirmar_response = client.post(
        f"/api/v1/reservas/{reserva_id}/confirmar",
        headers=admin_headers,
    )
    assert confirmar_response.status_code == 200, confirmar_response.text

    converter_response = client.post(
        f"/api/v1/reservas/{reserva_id}/converter",
        headers=admin_headers,
        json={
            "valor_diaria": 180,
            "tipo": "cliente",
            "hora_saida": "09:30",
            "combustivel_saida": "Cheio",
            "km_livres": 250,
            "valor_km_excedente": 1.9,
            "desconto": 20,
            "observacoes": "Cliente retirou com reserva confirmada",
        },
    )

    assert converter_response.status_code == 200, converter_response.text
    payload = converter_response.json()
    assert payload["numero"].startswith("CTR-RES-")
    assert float(payload["valor_total"]) == 520.0

    db_session.expire_all()
    reserva = db_session.query(Reserva).filter(Reserva.id == reserva_id).first()
    contrato = db_session.query(Contrato).filter(Contrato.id == payload["id"]).first()
    veiculo = db_session.query(Veiculo).filter(Veiculo.id == veiculo.id).first()
    checkins = db_session.query(CheckinCheckout).filter(CheckinCheckout.contrato_id == contrato.id).all()

    assert reserva.status == "convertida"
    assert contrato is not None
    assert contrato.status == "ativo"
    assert contrato.numero.startswith("CTR-RES-")
    assert float(contrato.km_inicial) == 8120.0
    assert contrato.combustivel_saida == "Cheio"
    assert float(contrato.km_livres) == 250.0
    assert float(contrato.valor_km_excedente) == 1.9
    assert int(contrato.qtd_diarias) == 3
    assert float(contrato.valor_total) == 520.0
    assert veiculo.status == "alugado"
    assert len(checkins) == 1
