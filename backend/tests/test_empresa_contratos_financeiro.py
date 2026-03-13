from datetime import date

from app.models import (
    Cliente,
    Contrato,
    DespesaVeiculo,
    Empresa,
    Manutencao,
    UsoVeiculoEmpresa,
    Veiculo,
)


def test_empresa_usage_syncs_with_indeterminate_contract(client, admin_headers, db_session):
    empresa = Empresa(nome="Empresa Alpha", cnpj="12345678000190", ativo=True)
    cliente = Cliente(
        nome="Gestor Empresa",
        cpf="12312312312",
        email="empresa.alpha@example.org",
        telefone="11999999999",
        empresa=empresa,
        ativo=True,
    )
    veiculo = Veiculo(
        placa="EMP1234",
        marca="Toyota",
        modelo="Yaris",
        km_atual=22000,
        status="disponivel",
        valor_diaria=3500,
        ativo=True,
    )
    db_session.add_all([empresa, cliente, veiculo])
    db_session.commit()
    db_session.refresh(empresa)
    db_session.refresh(cliente)
    db_session.refresh(veiculo)

    uso_response = client.post(
        f"/api/v1/empresas/{empresa.id}/usos",
        headers=admin_headers,
        json={
            "veiculo_id": veiculo.id,
            "data_inicio": "2026-03-01T00:00:00",
            "km_inicial": 22000,
            "km_referencia": 6000,
            "valor_km_extra": 1.75,
            "valor_diaria_empresa": 3500,
        },
    )
    assert uso_response.status_code == 200, uso_response.text
    uso_id = uso_response.json()["id"]

    contrato_response = client.post(
        "/api/v1/contratos/",
        headers=admin_headers,
        json={
          "cliente_id": cliente.id,
          "veiculo_id": veiculo.id,
          "tipo": "empresa",
          "vigencia_indeterminada": True,
          "empresa_uso_id": uso_id,
          "data_inicio": "2026-03-10T09:00:00",
          "valor_diaria": 3500,
          "km_livres": 6000,
          "valor_km_excedente": 1.75,
        },
    )
    assert contrato_response.status_code == 200, contrato_response.text
    contrato_id = contrato_response.json()["id"]

    db_session.expire_all()
    contrato = db_session.query(Contrato).filter(Contrato.id == contrato_id).first()
    uso = db_session.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()

    assert contrato is not None
    assert uso is not None
    assert contrato.tipo == "empresa"
    assert (contrato.data_fim - contrato.data_inicio).days >= 3600
    assert uso.contrato_id == contrato.id
    assert float(uso.valor_diaria_empresa) == 3500.0
    assert float(uso.valor_km_extra) == 1.75
    assert float(uso.km_referencia) == 6000.0

    close_response = client.post(
        f"/api/v1/contratos/{contrato_id}/encerrar",
        headers=admin_headers,
        json={
            "km_atual_veiculo": 29500,
            "status_pagamento": "pendente",
            "data_vencimento_pagamento": "2026-04-10",
        },
    )
    assert close_response.status_code == 200, close_response.text

    db_session.expire_all()
    uso = db_session.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
    assert uso.status == "finalizado"
    assert float(uso.km_final) == 29500.0
    assert float(uso.km_percorrido) == 7500.0


def test_veiculo_financial_history_consolidates_vehicle_costs(client, admin_headers, db_session):
    veiculo = Veiculo(
        placa="HST2026",
        marca="Honda",
        modelo="City",
        km_atual=10000,
        status="disponivel",
        data_aquisicao=date(2026, 1, 10),
        valor_aquisicao=55000,
        ativo=True,
    )
    cliente = Cliente(
        nome="Cliente Historico",
        cpf="55566677788",
        email="historico@example.org",
        telefone="11944445555",
        ativo=True,
    )
    db_session.add_all([veiculo, cliente])
    db_session.commit()
    db_session.refresh(veiculo)
    db_session.refresh(cliente)

    contrato_response = client.post(
        "/api/v1/contratos/",
        headers=admin_headers,
        json={
            "cliente_id": cliente.id,
            "veiculo_id": veiculo.id,
            "data_inicio": "2026-03-01T08:00:00",
            "data_fim": "2026-03-03T08:00:00",
            "valor_diaria": 200,
        },
    )
    assert contrato_response.status_code == 200, contrato_response.text
    contrato_id = contrato_response.json()["id"]

    close_response = client.post(
        f"/api/v1/contratos/{contrato_id}/encerrar",
        headers=admin_headers,
        json={"km_atual_veiculo": 10200, "status_pagamento": "pago"},
    )
    assert close_response.status_code == 200, close_response.text

    db_session.add(
        DespesaVeiculo(
            veiculo_id=veiculo.id,
            descricao="Troca de pneus",
            tipo="Pneus",
            valor=1200,
        )
    )
    db_session.add(
        Manutencao(
            veiculo_id=veiculo.id,
            tipo="preventiva",
            descricao="Revisao de 10.000 km",
            custo=650,
            status="concluida",
        )
    )
    db_session.commit()

    history_response = client.get(
        f"/api/v1/veiculos/historico-financeiro/{veiculo.id}",
        headers=admin_headers,
    )
    assert history_response.status_code == 200, history_response.text
    payload = history_response.json()

    categorias = {item["categoria"] for item in payload["records"]}
    assert "Aquisicao" in categorias
    assert "Pneus" in categorias
    assert "Manutencao / preventiva" in categorias
    assert "Contrato" in categorias
    assert payload["total_receita"] >= 400
    assert payload["total_despesa"] >= 56850
