from datetime import datetime, timedelta

from app.models import CheckinCheckout, Cliente, Contrato, Manutencao, Reserva, Veiculo


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
            "status_pagamento": "pago",
            "forma_pagamento": "Pix",
            "data_pagamento": "2026-03-13",
            "data_vencimento_pagamento": "2026-03-13",
            "valor_recebido": 570,
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
    assert contrato.status_pagamento == "pago"
    assert contrato.forma_pagamento == "Pix"
    assert float(contrato.valor_recebido) == 570.0
    assert float(veiculo.km_atual) == 15480
    assert veiculo.status == "disponivel"
    assert len(checkins) == 2
    devolucao = next(checkin for checkin in checkins if checkin.tipo == "devolucao")
    assert devolucao.itens_checklist["triangulo"] is False


def test_financeiro_reflects_contract_payment_status(client, admin_headers, db_session):
    cliente = Cliente(
        nome="Financeiro Cliente",
        cpf="55544433322",
        email="financeiro@example.org",
        telefone="11999990003",
        ativo=True,
    )
    veiculo = Veiculo(
        placa="FIN2026",
        marca="Nissan",
        modelo="Versa",
        km_atual=10200,
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
            "data_inicio": "2026-03-10T09:00:00",
            "data_fim": "2026-03-12T09:00:00",
            "valor_diaria": 200,
        },
    )

    assert create_response.status_code == 200, create_response.text
    contrato_id = create_response.json()["id"]

    close_response = client.post(
        f"/api/v1/contratos/{contrato_id}/encerrar",
        headers=admin_headers,
        json={
            "km_atual_veiculo": 10410,
            "status_pagamento": "pendente",
            "forma_pagamento": "Boleto",
            "data_vencimento_pagamento": "2026-03-20",
            "valor_recebido": 150,
        },
    )
    assert close_response.status_code == 200, close_response.text

    financeiro_response = client.get("/api/v1/financeiro/", headers=admin_headers)
    assert financeiro_response.status_code == 200, financeiro_response.text
    contrato_record = next(
        item for item in financeiro_response.json()["data"] if item["id"] == f"c-{contrato_id}"
    )
    assert contrato_record["status"] == "pendente"
    assert contrato_record["forma_pagamento"] == "Boleto"
    assert float(contrato_record["valor_recebido"]) == 150.0

    payment_response = client.patch(
        f"/api/v1/contratos/{contrato_id}/pagamento",
        headers=admin_headers,
        json={
            "status_pagamento": "pago",
            "forma_pagamento": "Pix",
            "data_pagamento": "2026-03-12",
            "valor_recebido": 400,
        },
    )
    assert payment_response.status_code == 200, payment_response.text
    assert payment_response.json()["status_pagamento"] == "pago"

    resumo_response = client.get("/api/v1/financeiro/resumo", headers=admin_headers)
    assert resumo_response.status_code == 200, resumo_response.text
    resumo = resumo_response.json()
    assert resumo["total_receita"] >= 400
    assert resumo["total_receita_recebida"] >= 400


def test_manutencao_blocks_vehicle_and_generates_alerts(client, admin_headers, db_session):
    veiculo = Veiculo(
        placa="MAN2026",
        marca="Fiat",
        modelo="Pulse",
        km_atual=20000,
        status="disponivel",
        ativo=True,
    )
    db_session.add(veiculo)
    db_session.commit()
    db_session.refresh(veiculo)

    create_response = client.post(
        "/api/v1/manutencoes/",
        headers=admin_headers,
        json={
            "veiculo_id": veiculo.id,
            "tipo": "preventiva",
            "descricao": "Revisao de 20 mil km",
            "status": "agendada",
            "oficina": "Oficina Centro",
            "custo": 350,
            "km_proxima": 19500,
            "data_proxima": (datetime.now() - timedelta(days=1)).date().isoformat(),
        },
    )

    assert create_response.status_code == 200, create_response.text
    manutencao_id = create_response.json()["id"]

    db_session.expire_all()
    veiculo = db_session.query(Veiculo).filter(Veiculo.id == veiculo.id).first()
    assert veiculo.status == "manutencao"

    resumo_response = client.get("/api/v1/manutencoes/resumo", headers=admin_headers)
    assert resumo_response.status_code == 200, resumo_response.text
    resumo = resumo_response.json()
    assert resumo["manutencoes_abertas"] == 1
    assert resumo["vencidas_por_data"] == 1
    assert resumo["vencidas_por_km"] == 1
    assert resumo["criticas"] == 1
    assert len(resumo["alertas"]) == 1
    assert resumo["alertas"][0]["placa"] == "MAN2026"

    complete_response = client.post(
        f"/api/v1/manutencoes/{manutencao_id}/completar",
        headers=admin_headers,
    )
    assert complete_response.status_code == 200, complete_response.text

    db_session.expire_all()
    manutencao = db_session.query(Manutencao).filter(Manutencao.id == manutencao_id).first()
    veiculo = db_session.query(Veiculo).filter(Veiculo.id == veiculo.id).first()

    assert manutencao.status == "concluida"
    assert float(manutencao.km_realizada) == 20000.0
    assert veiculo.status == "disponivel"


def test_dashboard_root_returns_operational_data(client, admin_headers, db_session):
    cliente = Cliente(
        nome="Dashboard Cliente",
        cpf="98765432100",
        email="dashboard@example.org",
        telefone="11999990001",
        ativo=True,
    )
    veiculo_atrasado = Veiculo(
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
    veiculo_manutencao = Veiculo(
        placa="MNT2026",
        marca="Fiat",
        modelo="Argo",
        km_atual=12500,
        status="manutencao",
        ativo=True,
    )
    veiculo_retirada = Veiculo(
        placa="RET2026",
        marca="Hyundai",
        modelo="HB20",
        km_atual=17400,
        status="alugado",
        ativo=True,
    )
    veiculo_devolucao = Veiculo(
        placa="DEV2026",
        marca="Toyota",
        modelo="Yaris",
        km_atual=26100,
        status="alugado",
        ativo=True,
    )
    db_session.add_all(
        [cliente, veiculo_atrasado, veiculo_livre, veiculo_manutencao, veiculo_retirada, veiculo_devolucao]
    )
    db_session.commit()
    db_session.refresh(cliente)
    db_session.refresh(veiculo_atrasado)
    db_session.refresh(veiculo_livre)
    db_session.refresh(veiculo_manutencao)
    db_session.refresh(veiculo_retirada)
    db_session.refresh(veiculo_devolucao)

    contrato_atrasado = Contrato(
        numero="CTR-DASH-1",
        cliente_id=cliente.id,
        veiculo_id=veiculo_atrasado.id,
        data_inicio=datetime.now() - timedelta(days=5),
        data_fim=datetime.now() - timedelta(days=1),
        km_inicial=22000,
        valor_diaria=150,
        valor_total=750,
        status="ativo",
        qtd_diarias=5,
        tipo="cliente",
    )
    contrato_retirada = Contrato(
        numero="CTR-DASH-2",
        cliente_id=cliente.id,
        veiculo_id=veiculo_retirada.id,
        data_inicio=datetime.now() - timedelta(hours=2),
        data_fim=datetime.now() + timedelta(days=2),
        km_inicial=17400,
        valor_diaria=180,
        valor_total=540,
        status="ativo",
        qtd_diarias=3,
        tipo="cliente",
    )
    contrato_devolucao = Contrato(
        numero="CTR-DASH-3",
        cliente_id=cliente.id,
        veiculo_id=veiculo_devolucao.id,
        data_inicio=datetime.now() - timedelta(days=3),
        data_fim=datetime.now() + timedelta(hours=3),
        km_inicial=26100,
        valor_diaria=210,
        valor_total=840,
        status="ativo",
        qtd_diarias=4,
        tipo="cliente",
    )
    reserva = Reserva(
        cliente_id=cliente.id,
        veiculo_id=veiculo_livre.id,
        data_inicio=datetime.now() + timedelta(hours=1),
        data_fim=datetime.now() + timedelta(days=2),
        status="pendente",
        valor_estimado=390,
    )
    manutencao = Manutencao(
        veiculo_id=veiculo_manutencao.id,
        tipo="preventiva",
        descricao="Troca de oleo",
        data_proxima=datetime.now().date(),
        custo=220,
        oficina="Oficina Centro",
        status="agendada",
    )
    db_session.add_all([contrato_atrasado, contrato_retirada, contrato_devolucao, reserva, manutencao])
    db_session.commit()

    response = client.get("/api/v1/dashboard/", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_veiculos"] == 5
    assert body["veiculos_alugados"] == 3
    assert body["veiculos_disponiveis"] == 1
    assert body["veiculos_manutencao"] == 1
    assert body["contratos_ativos"] == 3
    assert body["total_clientes"] == 1
    assert body["reservas_pendentes"] == 1
    assert body["manutencoes_abertas"] == 1
    assert body["retiradas_hoje"] == 1
    assert body["devolucoes_hoje"] == 1
    assert len(body["receita_vs_despesas"]) == 6
    assert body["top_clientes"][0]["nome"] == "Dashboard Cliente"
    assert {item["placa"] for item in body["top_veiculos"]} >= {"XYZ9876", "RET2026", "DEV2026"}
    assert len(body["contratos_atrasados"]) == 1
    assert len(body["alertas"]) >= 1
    assert len(body["agenda_hoje"]) >= 3
    assert {item["rota"] for item in body["agenda_hoje"]} >= {"/reservas", "/contratos", "/manutencoes"}


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
