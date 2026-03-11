from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.models.user import User, ALL_PAGES
from app.models import (
    Configuracao, IpvaAliquota, Cliente, Veiculo, Contrato,
    Empresa, DespesaContrato, DespesaVeiculo, DespesaLoja,
    DespesaOperacional, Seguro, ParcelaSeguro, IpvaRegistro,
    Reserva, Multa, Manutencao, RelatorioNF, UsoVeiculoEmpresa,
)
from app.core.security import get_password_hash


def seed_database(db: Session):
    """Seed the database with initial data."""

    # Check if admin user already exists
    admin_exists = db.query(User).filter(User.email == "admin@mpcars.com").first()
    if not admin_exists:
        admin_user = User(
            email="admin@mpcars.com",
            hashed_password=get_password_hash("123456"),
            nome="Administrador",
            perfil="admin",
            ativo=True,
            permitted_pages=ALL_PAGES,
        )
        db.add(admin_user)
        db.commit()
    else:
        # Ensure existing admin has all pages
        if not admin_exists.permitted_pages or len(admin_exists.permitted_pages) < len(ALL_PAGES):
            admin_exists.permitted_pages = ALL_PAGES
            db.commit()

    # Check if configurations already exist
    config_count = db.query(Configuracao).count()
    if config_count == 0:
        configurations = [
            Configuracao(chave="empresa_nome", valor="MPCARS Aluguel de Veiculos"),
            Configuracao(chave="empresa_cnpj", valor="12.345.678/0001-90"),
            Configuracao(chave="empresa_telefone", valor="(84) 99999-9999"),
            Configuracao(chave="empresa_email", valor="contato@mpcars.com"),
            Configuracao(chave="empresa_endereco", valor="Rua Principal, 100 - Centro, Pau dos Ferros/RN"),
            Configuracao(chave="valor_diaria_padrao", valor="150.00"),
            Configuracao(chave="km_limite_manutencao", valor="5000"),
            Configuracao(chave="dias_alerta_vencimento", valor="30"),
            Configuracao(chave="taxa_multa_atraso", valor="50.00"),
            Configuracao(chave="percentual_caucao", valor="10"),
            Configuracao(chave="sistema_versao", valor="2.0.0"),
            Configuracao(chave="timezone", valor="America/Sao_Paulo"),
        ]
        db.add_all(configurations)
        db.commit()

    # Check if IPVA aliquotas already exist
    ipva_count = db.query(IpvaAliquota).count()
    if ipva_count == 0:
        states = ["SP", "RJ", "MG", "BA", "SC", "PR", "RS", "DF", "RN", "CE"]
        types = ["Automovel", "Moto", "Utilitario", "Caminhao"]
        ipva_rates = {
            "SP": {"Automovel": 4.0, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "RJ": {"Automovel": 3.5, "Moto": 1.0, "Utilitario": 2.0, "Caminhao": 2.5},
            "MG": {"Automovel": 3.5, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "BA": {"Automovel": 3.0, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "SC": {"Automovel": 3.5, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "PR": {"Automovel": 3.5, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "RS": {"Automovel": 3.5, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.5},
            "DF": {"Automovel": 4.5, "Moto": 2.0, "Utilitario": 2.5, "Caminhao": 3.0},
            "RN": {"Automovel": 3.0, "Moto": 1.0, "Utilitario": 1.5, "Caminhao": 1.0},
            "CE": {"Automovel": 3.0, "Moto": 1.5, "Utilitario": 2.0, "Caminhao": 2.0},
        }
        ipva_records = []
        for state in states:
            for vehicle_type in types:
                aliquota = IpvaAliquota(
                    estado=state,
                    tipo_veiculo=vehicle_type,
                    aliquota=ipva_rates[state][vehicle_type],
                    descricao=f"Aliquota IPVA {state} - {vehicle_type}",
                )
                ipva_records.append(aliquota)
        db.add_all(ipva_records)
        db.commit()

    # === SEED MOCKUP DATA ===
    # Only seed if no clients exist yet
    cliente_count = db.query(Cliente).count()
    if cliente_count > 0:
        return

    # --- EMPRESAS ---
    empresas = [
        Empresa(
            nome="TransLog Nordeste",
            cnpj="11.222.333/0001-44",
            razao_social="TransLog Nordeste Transportes LTDA",
            endereco="Av. Industrial, 500",
            cidade="Mossoró",
            estado="RN",
            cep="59600-000",
            telefone="(84) 3322-1100",
            email="contato@translog.com.br",
            contato_principal="Roberto Almeida",
            ativo=True,
        ),
        Empresa(
            nome="Agro Serra Verde",
            cnpj="44.555.666/0001-77",
            razao_social="Agro Serra Verde Comercio LTDA",
            endereco="Rod. BR-405, Km 12",
            cidade="Pau dos Ferros",
            estado="RN",
            cep="59900-000",
            telefone="(84) 3351-2200",
            email="contato@agroserra.com.br",
            contato_principal="Maria das Gracas",
            ativo=True,
        ),
        Empresa(
            nome="Tech Solutions CE",
            cnpj="77.888.999/0001-11",
            razao_social="Tech Solutions CE Informatica LTDA",
            endereco="Rua da Tecnologia, 88",
            cidade="Fortaleza",
            estado="CE",
            cep="60000-000",
            telefone="(85) 3244-5566",
            email="contato@techsolutions.com.br",
            contato_principal="Carlos Eduardo",
            ativo=True,
        ),
    ]
    db.add_all(empresas)
    db.commit()

    # --- CLIENTES (Pessoa Fisica) ---
    clientes_pf = [
        Cliente(
            nome="Joao Silva Santos",
            cpf="123.456.789-00",
            rg="1234567",
            data_nascimento=date(1985, 3, 15),
            telefone="(84) 99988-7766",
            email="joao.silva@email.com",
            endereco_residencial="Rua das Flores, 45",
            numero_residencial="45",
            cidade_residencial="Pau dos Ferros",
            estado_residencial="RN",
            cep_residencial="59900-000",
            numero_cnh="12345678900",
            validade_cnh=date(2027, 5, 20),
            categoria_cnh="AB",
            score=95,
            ativo=True,
        ),
        Cliente(
            nome="Maria Fernanda Oliveira",
            cpf="987.654.321-00",
            rg="7654321",
            data_nascimento=date(1990, 7, 22),
            telefone="(84) 99877-6655",
            email="maria.fernanda@email.com",
            endereco_residencial="Av. Brasil, 200",
            numero_residencial="200",
            cidade_residencial="Mossoro",
            estado_residencial="RN",
            cep_residencial="59600-000",
            numero_cnh="98765432100",
            validade_cnh=date(2026, 11, 10),
            categoria_cnh="B",
            score=88,
            ativo=True,
        ),
        Cliente(
            nome="Carlos Eduardo Pereira",
            cpf="456.789.123-00",
            rg="4567891",
            data_nascimento=date(1978, 12, 5),
            telefone="(85) 99766-5544",
            email="carlos.pereira@email.com",
            endereco_residencial="Rua do Comercio, 78",
            numero_residencial="78",
            cidade_residencial="Fortaleza",
            estado_residencial="CE",
            cep_residencial="60000-000",
            numero_cnh="45678912300",
            validade_cnh=date(2025, 8, 15),
            categoria_cnh="AB",
            score=75,
            ativo=True,
        ),
        Cliente(
            nome="Ana Beatriz Costa",
            cpf="321.654.987-00",
            rg="3216549",
            data_nascimento=date(1995, 1, 30),
            telefone="(84) 99655-4433",
            email="ana.costa@email.com",
            endereco_residencial="Rua Nova, 150",
            numero_residencial="150",
            cidade_residencial="Caico",
            estado_residencial="RN",
            cep_residencial="59300-000",
            numero_cnh="32165498700",
            validade_cnh=date(2028, 2, 28),
            categoria_cnh="B",
            score=100,
            ativo=True,
        ),
        Cliente(
            nome="Pedro Henrique Lima",
            cpf="654.321.987-00",
            rg="6543219",
            data_nascimento=date(1982, 9, 18),
            telefone="(84) 99544-3322",
            email="pedro.lima@email.com",
            endereco_residencial="Travessa Boa Vista, 33",
            numero_residencial="33",
            cidade_residencial="Natal",
            estado_residencial="RN",
            cep_residencial="59000-000",
            numero_cnh="65432198700",
            validade_cnh=date(2026, 6, 1),
            categoria_cnh="AB",
            score=82,
            ativo=True,
        ),
        Cliente(
            nome="Francisca Souza Mendes",
            cpf="789.123.456-00",
            rg="7891234",
            data_nascimento=date(1988, 4, 12),
            telefone="(84) 99433-2211",
            email="francisca.souza@email.com",
            endereco_residencial="Rua Sao Jose, 67",
            numero_residencial="67",
            cidade_residencial="Pau dos Ferros",
            estado_residencial="RN",
            cep_residencial="59900-000",
            numero_cnh="78912345600",
            validade_cnh=date(2027, 9, 15),
            categoria_cnh="B",
            score=90,
            empresa_id=1,
            ativo=True,
        ),
    ]
    db.add_all(clientes_pf)
    db.commit()

    # --- VEICULOS ---
    veiculos = [
        Veiculo(
            placa="RNP-1A23",
            marca="Toyota",
            modelo="Corolla XEi",
            ano=2023,
            cor="Prata",
            chassis="9BR53ZEC6P1234567",
            renavam="12345678901",
            combustivel="Flex",
            capacidade_tanque=50.0,
            km_atual=15000.0,
            data_aquisicao=date(2023, 1, 15),
            valor_aquisicao=Decimal("135000.00"),
            status="alugado",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-2B34",
            marca="Hyundai",
            modelo="HB20 Comfort",
            ano=2024,
            cor="Branco",
            chassis="9BHB4115XP2345678",
            renavam="23456789012",
            combustivel="Flex",
            capacidade_tanque=50.0,
            km_atual=8000.0,
            data_aquisicao=date(2024, 3, 10),
            valor_aquisicao=Decimal("82000.00"),
            status="disponivel",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-3C45",
            marca="Chevrolet",
            modelo="Onix Plus LTZ",
            ano=2023,
            cor="Preto",
            chassis="9BGKF48X0PG345678",
            renavam="34567890123",
            combustivel="Flex",
            capacidade_tanque=44.0,
            km_atual=22000.0,
            data_aquisicao=date(2023, 6, 20),
            valor_aquisicao=Decimal("95000.00"),
            status="alugado",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-4D56",
            marca="Fiat",
            modelo="Strada Endurance",
            ano=2024,
            cor="Vermelho",
            chassis="9BD19573XP4567890",
            renavam="45678901234",
            combustivel="Flex",
            capacidade_tanque=48.0,
            km_atual=5000.0,
            data_aquisicao=date(2024, 1, 5),
            valor_aquisicao=Decimal("105000.00"),
            status="disponivel",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-5E67",
            marca="Volkswagen",
            modelo="T-Cross Comfortline",
            ano=2023,
            cor="Cinza",
            chassis="9BWAB45U0PT567890",
            renavam="56789012345",
            combustivel="Flex",
            capacidade_tanque=50.0,
            km_atual=30000.0,
            data_aquisicao=date(2023, 2, 28),
            valor_aquisicao=Decimal("128000.00"),
            status="manutencao",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-6F78",
            marca="Renault",
            modelo="Kwid Zen",
            ano=2024,
            cor="Azul",
            chassis="93YBSR35HP6789012",
            renavam="67890123456",
            combustivel="Flex",
            capacidade_tanque=28.0,
            km_atual=3500.0,
            data_aquisicao=date(2024, 5, 15),
            valor_aquisicao=Decimal("68000.00"),
            status="disponivel",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-7G89",
            marca="Toyota",
            modelo="Hilux SRV",
            ano=2022,
            cor="Prata",
            chassis="9BR53ZEC2N7890123",
            renavam="78901234567",
            combustivel="Diesel",
            capacidade_tanque=80.0,
            km_atual=55000.0,
            data_aquisicao=date(2022, 8, 10),
            valor_aquisicao=Decimal("245000.00"),
            status="alugado",
            ativo=True,
        ),
        Veiculo(
            placa="RNP-8H90",
            marca="Jeep",
            modelo="Renegade Sport",
            ano=2023,
            cor="Verde",
            chassis="9BJAN1210PP890123",
            renavam="89012345678",
            combustivel="Flex",
            capacidade_tanque=48.0,
            km_atual=18000.0,
            data_aquisicao=date(2023, 4, 22),
            valor_aquisicao=Decimal("115000.00"),
            status="disponivel",
            ativo=True,
        ),
    ]
    db.add_all(veiculos)
    db.commit()

    # --- CONTRATOS ---
    now = datetime.now()
    contratos = [
        Contrato(
            numero="CT-2025-001",
            cliente_id=1,
            veiculo_id=1,
            data_inicio=now - timedelta(days=30),
            data_fim=now + timedelta(days=60),
            km_inicial=14500.0,
            valor_diaria=Decimal("180.00"),
            valor_total=Decimal("16200.00"),
            status="ativo",
            observacoes="Contrato pessoa fisica - Joao Silva",
        ),
        Contrato(
            numero="CT-2025-002",
            cliente_id=2,
            veiculo_id=3,
            data_inicio=now - timedelta(days=15),
            data_fim=now + timedelta(days=45),
            km_inicial=21500.0,
            valor_diaria=Decimal("150.00"),
            valor_total=Decimal("9000.00"),
            status="ativo",
            observacoes="Contrato pessoa fisica - Maria Fernanda",
        ),
        Contrato(
            numero="CT-2025-003",
            cliente_id=6,
            veiculo_id=7,
            data_inicio=now - timedelta(days=60),
            data_fim=now - timedelta(days=5),
            km_inicial=50000.0,
            km_final=54200.0,
            valor_diaria=Decimal("350.00"),
            valor_total=Decimal("19250.00"),
            status="finalizado",
            data_finalizacao=now - timedelta(days=5),
            observacoes="Contrato empresa TransLog - Hilux SRV",
        ),
        Contrato(
            numero="CT-2025-004",
            cliente_id=3,
            veiculo_id=5,
            data_inicio=now - timedelta(days=90),
            data_fim=now - timedelta(days=10),
            km_inicial=28000.0,
            km_final=29800.0,
            valor_diaria=Decimal("200.00"),
            valor_total=Decimal("16000.00"),
            status="finalizado",
            data_finalizacao=now - timedelta(days=8),
            observacoes="Contrato pessoa fisica - Carlos Eduardo",
        ),
        Contrato(
            numero="CT-2025-005",
            cliente_id=4,
            veiculo_id=2,
            data_inicio=now - timedelta(days=5),
            data_fim=now + timedelta(days=25),
            km_inicial=7800.0,
            valor_diaria=Decimal("120.00"),
            valor_total=Decimal("3600.00"),
            status="ativo",
            observacoes="Contrato pessoa fisica - Ana Beatriz",
        ),
        Contrato(
            numero="CT-2024-010",
            cliente_id=5,
            veiculo_id=4,
            data_inicio=now - timedelta(days=120),
            data_fim=now - timedelta(days=60),
            km_inicial=3000.0,
            km_final=4800.0,
            valor_diaria=Decimal("160.00"),
            valor_total=Decimal("9600.00"),
            status="finalizado",
            data_finalizacao=now - timedelta(days=58),
            observacoes="Contrato pessoa fisica - Pedro Henrique",
        ),
    ]
    db.add_all(contratos)
    db.commit()

    # --- DESPESAS DE CONTRATO ---
    despesas_contrato = [
        DespesaContrato(contrato_id=1, tipo="Combustivel", descricao="Abastecimento inicial", valor=Decimal("250.00"), responsavel="admin@mpcars.com"),
        DespesaContrato(contrato_id=1, tipo="Lavagem", descricao="Lavagem completa entrega", valor=Decimal("80.00"), responsavel="admin@mpcars.com"),
        DespesaContrato(contrato_id=2, tipo="Combustivel", descricao="Abastecimento inicial", valor=Decimal("200.00"), responsavel="admin@mpcars.com"),
        DespesaContrato(contrato_id=3, tipo="Pedagio", descricao="Pedagios BR-304", valor=Decimal("120.00"), responsavel="admin@mpcars.com"),
        DespesaContrato(contrato_id=3, tipo="Combustivel", descricao="3 abastecimentos diesel", valor=Decimal("850.00"), responsavel="admin@mpcars.com"),
        DespesaContrato(contrato_id=4, tipo="Multa", descricao="Multa velocidade BR-405", valor=Decimal("293.47"), responsavel="admin@mpcars.com"),
    ]
    db.add_all(despesas_contrato)
    db.commit()

    # --- DESPESAS VEICULO ---
    despesas_veiculo = [
        DespesaVeiculo(veiculo_id=1, valor=Decimal("450.00"), descricao="Troca de oleo e filtro", km=14000.0),
        DespesaVeiculo(veiculo_id=1, valor=Decimal("1200.00"), descricao="Troca de pneus dianteiros", km=13000.0, pneu=True),
        DespesaVeiculo(veiculo_id=3, valor=Decimal("380.00"), descricao="Revisao 20.000km", km=20000.0),
        DespesaVeiculo(veiculo_id=5, valor=Decimal("2500.00"), descricao="Troca de pastilhas e discos", km=28000.0),
        DespesaVeiculo(veiculo_id=7, valor=Decimal("650.00"), descricao="Troca oleo diesel", km=50000.0),
        DespesaVeiculo(veiculo_id=7, valor=Decimal("3200.00"), descricao="Troca de 4 pneus", km=48000.0, pneu=True),
    ]
    db.add_all(despesas_veiculo)
    db.commit()

    # --- DESPESAS LOJA ---
    despesas_loja = [
        DespesaLoja(mes=1, ano=2025, valor=Decimal("3500.00"), descricao="Aluguel escritorio"),
        DespesaLoja(mes=1, ano=2025, valor=Decimal("450.00"), descricao="Energia eletrica"),
        DespesaLoja(mes=1, ano=2025, valor=Decimal("180.00"), descricao="Internet e telefone"),
        DespesaLoja(mes=2, ano=2025, valor=Decimal("3500.00"), descricao="Aluguel escritorio"),
        DespesaLoja(mes=2, ano=2025, valor=Decimal("520.00"), descricao="Energia eletrica"),
        DespesaLoja(mes=2, ano=2025, valor=Decimal("180.00"), descricao="Internet e telefone"),
        DespesaLoja(mes=3, ano=2025, valor=Decimal("3500.00"), descricao="Aluguel escritorio"),
        DespesaLoja(mes=3, ano=2025, valor=Decimal("480.00"), descricao="Energia eletrica"),
    ]
    db.add_all(despesas_loja)
    db.commit()

    # --- SEGUROS ---
    seguros = [
        Seguro(
            veiculo_id=1, seguradora="Porto Seguro", numero_apolice="PS-2025-001",
            tipo_seguro="Completo", data_inicio=date(2025, 1, 1), data_fim=date(2026, 1, 1),
            valor=Decimal("4800.00"), valor_franquia=Decimal("3200.00"), status="ativo", qtd_parcelas=12,
        ),
        Seguro(
            veiculo_id=3, seguradora="Bradesco Seguros", numero_apolice="BS-2025-002",
            tipo_seguro="Completo", data_inicio=date(2025, 2, 1), data_fim=date(2026, 2, 1),
            valor=Decimal("3600.00"), valor_franquia=Decimal("2800.00"), status="ativo", qtd_parcelas=12,
        ),
        Seguro(
            veiculo_id=5, seguradora="Azul Seguros", numero_apolice="AZ-2025-003",
            tipo_seguro="Terceiros", data_inicio=date(2025, 1, 15), data_fim=date(2026, 1, 15),
            valor=Decimal("1800.00"), valor_franquia=Decimal("1500.00"), status="ativo", qtd_parcelas=6,
        ),
        Seguro(
            veiculo_id=7, seguradora="Porto Seguro", numero_apolice="PS-2024-010",
            tipo_seguro="Completo", data_inicio=date(2024, 8, 1), data_fim=date(2025, 8, 1),
            valor=Decimal("8500.00"), valor_franquia=Decimal("5000.00"), status="ativo", qtd_parcelas=12,
        ),
    ]
    db.add_all(seguros)
    db.commit()
    # Refresh to get actual IDs from database
    for seguro in seguros:
        db.refresh(seguro)

    # --- PARCELAS SEGURO ---
    parcelas = []
    for seguro in seguros:
        # Use actual persisted ID instead of assuming sequential IDs
        for i in range(1, (seguro.qtd_parcelas or 12) + 1):
            venc = seguro.data_inicio + timedelta(days=30 * i)
            pago = venc < date.today()
            parcelas.append(ParcelaSeguro(
                seguro_id=seguro.id, veiculo_id=seguro.veiculo_id,
                numero_parcela=i, valor=Decimal(str(round(float(seguro.valor) / (seguro.qtd_parcelas or 12), 2))),
                vencimento=venc,
                data_pagamento=venc if pago else None,
                status="pago" if pago else "pendente",
            ))
    db.add_all(parcelas)
    db.commit()

    # --- IPVA REGISTROS ---
    ipva_registros = [
        IpvaRegistro(veiculo_id=1, ano_referencia=2025, valor_venal=Decimal("120000.00"), aliquota=3.0, valor_ipva=Decimal("3600.00"), valor_pago=Decimal("3600.00"), data_vencimento=date(2025, 3, 15), status="pago"),
        IpvaRegistro(veiculo_id=2, ano_referencia=2025, valor_venal=Decimal("75000.00"), aliquota=3.0, valor_ipva=Decimal("2250.00"), valor_pago=Decimal("0.00"), data_vencimento=date(2025, 4, 15), status="pendente"),
        IpvaRegistro(veiculo_id=3, ano_referencia=2025, valor_venal=Decimal("85000.00"), aliquota=3.0, valor_ipva=Decimal("2550.00"), valor_pago=Decimal("2550.00"), data_vencimento=date(2025, 3, 15), status="pago"),
        IpvaRegistro(veiculo_id=4, ano_referencia=2025, valor_venal=Decimal("95000.00"), aliquota=3.0, valor_ipva=Decimal("2850.00"), valor_pago=Decimal("0.00"), data_vencimento=date(2025, 5, 15), status="pendente"),
        IpvaRegistro(veiculo_id=5, ano_referencia=2025, valor_venal=Decimal("110000.00"), aliquota=3.0, valor_ipva=Decimal("3300.00"), valor_pago=Decimal("1650.00"), data_vencimento=date(2025, 3, 15), status="parcial"),
        IpvaRegistro(veiculo_id=7, ano_referencia=2025, valor_venal=Decimal("200000.00"), aliquota=3.0, valor_ipva=Decimal("6000.00"), valor_pago=Decimal("6000.00"), data_vencimento=date(2025, 2, 15), status="pago"),
    ]
    db.add_all(ipva_registros)
    db.commit()

    # --- MULTAS ---
    multas = [
        Multa(veiculo_id=1, contrato_id=1, cliente_id=1, data_infracao=date(2025, 2, 10), valor=Decimal("130.16"), pontos=4, gravidade="media", status="pendente", responsavel="condutor"),
        Multa(veiculo_id=3, contrato_id=2, cliente_id=2, data_infracao=date(2025, 2, 20), valor=Decimal("293.47"), pontos=7, gravidade="grave", status="pago", responsavel="condutor"),
        Multa(veiculo_id=7, contrato_id=3, cliente_id=6, data_infracao=date(2025, 1, 15), valor=Decimal("88.38"), pontos=3, gravidade="leve", status="pendente", responsavel="empresa"),
    ]
    db.add_all(multas)
    db.commit()

    # --- MANUTENCOES ---
    manutencoes = [
        Manutencao(veiculo_id=1, tipo="Preventiva", descricao="Troca de oleo e filtro 15.000km", km_realizada=14000.0, km_proxima=19000.0, data_realizada=date(2025, 1, 10), data_proxima=date(2025, 7, 10), custo=Decimal("450.00"), oficina="Auto Center Pau dos Ferros", status="concluida"),
        Manutencao(veiculo_id=3, tipo="Preventiva", descricao="Revisao 20.000km completa", km_realizada=20000.0, km_proxima=30000.0, data_realizada=date(2025, 2, 5), data_proxima=date(2025, 8, 5), custo=Decimal("380.00"), oficina="Chevrolet Concessionaria", status="concluida"),
        Manutencao(veiculo_id=5, tipo="Corretiva", descricao="Troca de pastilhas e discos de freio", km_realizada=28000.0, data_realizada=date(2025, 2, 25), custo=Decimal("2500.00"), oficina="FreioTech", status="em_andamento"),
        Manutencao(veiculo_id=7, tipo="Preventiva", descricao="Troca oleo diesel + filtros", km_realizada=50000.0, km_proxima=60000.0, data_realizada=date(2025, 1, 20), data_proxima=date(2025, 7, 20), custo=Decimal("650.00"), oficina="Toyota Natal", status="concluida"),
        Manutencao(veiculo_id=2, tipo="Preventiva", descricao="Revisao 10.000km agendada", km_proxima=10000.0, data_proxima=date(2025, 6, 1), status="agendada"),
    ]
    db.add_all(manutencoes)
    db.commit()

    # --- RESERVAS ---
    reservas = [
        Reserva(cliente_id=3, veiculo_id=6, data_inicio=now + timedelta(days=5), data_fim=now + timedelta(days=15), status="confirmada", valor_estimado=Decimal("1200.00")),
        Reserva(cliente_id=5, veiculo_id=8, data_inicio=now + timedelta(days=10), data_fim=now + timedelta(days=30), status="pendente", valor_estimado=Decimal("3400.00")),
        Reserva(cliente_id=4, veiculo_id=4, data_inicio=now + timedelta(days=30), data_fim=now + timedelta(days=45), status="pendente", valor_estimado=Decimal("2400.00")),
    ]
    db.add_all(reservas)
    db.commit()

    # --- USO VEICULO EMPRESA ---
    uso_empresa = [
        UsoVeiculoEmpresa(
            veiculo_id=7, empresa_id=1, contrato_id=3,
            km_inicial=50000.0, km_final=54200.0,
            data_inicio=now - timedelta(days=60), data_fim=now - timedelta(days=5),
            km_referencia=3000.0, valor_km_extra=Decimal("1.50"),
            status="finalizado",
        ),
    ]
    db.add_all(uso_empresa)
    db.commit()

    # --- RELATORIO NF ---
    relatorio_nf = [
        RelatorioNF(
            veiculo_id=7, empresa_id=1, uso_id=1,
            periodo_inicio=date(2025, 1, 1), periodo_fim=date(2025, 2, 28),
            km_percorrida=4200.0, km_excedente=1200.0,
            valor_total_extra=Decimal("1800.00"),
        ),
    ]
    db.add_all(relatorio_nf)
    db.commit()

    print("=== Seed data inserido com sucesso! ===")
    print(f"  Empresas: {len(empresas)}")
    print(f"  Clientes: {len(clientes_pf)}")
    print(f"  Veiculos: {len(veiculos)}")
    print(f"  Contratos: {len(contratos)}")
    print(f"  Seguros: {len(seguros)}")
    print(f"  Multas: {len(multas)}")
    print(f"  Manutencoes: {len(manutencoes)}")
    print(f"  Reservas: {len(reservas)}")
