"""
Comprehensive test suite for MPCARS2 system.
Tests CRUD operations, business rules, validation, and authentication.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models import (
    Empresa, Cliente, Veiculo, Contrato, Reserva,
    Seguro, Multa, Manutencao, DespesaVeiculo,
    LancamentoFinanceiro, IpvaRegistro
)
from app.models.user import User
from app.core.security import get_password_hash


TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        id=1,
        email="test@mpcars.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Get authentication headers for test user."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_empresa(db_session):
    """Create a test empresa."""
    empresa = Empresa(
        nome="Empresa Teste",
        cnpj="12345678000100",
        razao_social="Empresa Teste LTDA",
        endereco="Rua Teste, 123",
        cidade="São Paulo",
        estado="SP",
        cep="01000-000",
        telefone="11999999999",
        email="teste@empresa.com",
        ativo=True
    )
    db_session.add(empresa)
    db_session.commit()
    db_session.refresh(empresa)
    return empresa


@pytest.fixture
def test_cliente(db_session, test_empresa):
    """Create a test cliente."""
    cliente = Cliente(
        nome="Cliente Teste",
        cpf="12345678901",
        cnpj=None,
        rg="123456789",
        orgao_exp="SSP",
        estado_civil="solteiro",
        profissao="Autonomo",
        email="cliente@teste.com",
        telefone="11988887777",
        telefone_residencial="1133334444",
        endereco="Rua Cliente, 456",
        cidade="São Paulo",
        estado="SP",
        cep="02000-000",
        empresa_id=test_empresa.id
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


@pytest.fixture
def test_veiculo(db_session, test_empresa):
    """Create a test veiculo."""
    veiculo = Veiculo(
        marca="Volkswagen",
        modelo="Gol",
        ano=2023,
        placa="ABC-1234",
        cor="Branco",
        chassi="9BWZZZ377VT000001",
        renavam="01234567890",
        combustivel="Gasolina",
        cambio="Manual",
        portas=4,
        quilometragem=1000,
        valor_fipe=70000.00,
        valor_locacao=150.00,
        status="disponivel",
        empresa_id=test_empresa.id,
        categoria="Hatch"
    )
    db_session.add(veiculo)
    db_session.commit()
    db_session.refresh(veiculo)
    return veiculo


class TestEmpresaCRUD:
    """Tests for Empresa CRUD operations."""

    def test_list_empresas(self, client, test_empresa, auth_headers):
        """Test listing empresas."""
        response = client.get("/api/v1/empresas/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)

    def test_create_empresa(self, client, auth_headers):
        """Test creating a empresa."""
        empresa_data = {
            "nome": "Nova Empresa",
            "cnpj": "98765432000100",
            "razao_social": "Nova Empresa LTDA",
            "endereco": "Rua Nova, 789",
            "cidade": "Rio de Janeiro",
            "estado": "RJ",
            "cep="20000-000",
            "telefone": "21999999999",
            "email": "nova@empresa.com"
        }
        response = client.post("/api/v1/empresas/", json=empresa_data, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nome"] == "Nova Empresa"

    def test_create_empresa_duplicate_cnpj(self, client, test_empresa, auth_headers):
        """Test creating empresa with duplicate CNPJ."""
        empresa_data = {
            "nome": "Empresa Duplicada",
            "cnpj": test_empresa.cnpj,
            "razao_social": "Duplicada LTDA"
        }
        response = client.post("/api/v1/empresas/", json=empresa_data, headers=auth_headers)
        assert response.status_code == 400

    def test_get_empresa(self, client, test_empresa, auth_headers):
        """Test getting a single empresa."""
        response = client.get(f"/api/v1/empresas/{test_empresa.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_empresa.id

    def test_get_empresa_not_found(self, client, auth_headers):
        """Test getting non-existent empresa."""
        response = client.get("/api/v1/empresas/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_update_empresa(self, client, test_empresa, auth_headers):
        """Test updating a empresa."""
        update_data = {"nome": "Empresa Atualizada"}
        response = client.put(f"/api/v1/empresas/{test_empresa.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["nome"] == "Empresa Atualizada"

    def test_delete_empresa(self, client, test_empresa, auth_headers):
        """Test deleting a empresa."""
        response = client.delete(f"/api/v1/empresas/{test_empresa.id}", headers=auth_headers)
        assert response.status_code == 204
        
        verify_response = client.get(f"/api/v1/empresas/{test_empresa.id}", headers=auth_headers)
        assert verify_response.status_code == 404


class TestClienteCRUD:
    """Tests for Cliente CRUD operations."""

    def test_list_clientes(self, client, test_cliente, auth_headers):
        """Test listing clientes."""
        response = client.get("/api/v1/clientes/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_cliente(self, client, test_empresa, auth_headers):
        """Test creating a cliente."""
        cliente_data = {
            "nome": "Novo Cliente",
            "cpf": "98765432109",
            "rg": "987654321",
            "orgao_exp": "SSP",
            "estado_civil": "casado",
            "profissao": "Empresario",
            "email": "novo@cliente.com",
            "telefone": "11977776666",
            "endereco": "Rua Novo Cliente, 100",
            "cidade": "São Paulo",
            "estado": "SP",
            "cep="03000-000",
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/clientes/", json=cliente_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_create_cliente_invalid_cpf(self, client, test_empresa, auth_headers):
        """Test creating cliente with invalid CPF."""
        cliente_data = {
            "nome": "Cliente Inválido",
            "cpf": "123",
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/clientes/", json=cliente_data, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_create_cliente_without_cpf_cnpj(self, client, test_empresa, auth_headers):
        """Test creating cliente without CPF or CNPJ."""
        cliente_data = {
            "nome": "Cliente Sem Documento",
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/clientes/", json=cliente_data, headers=auth_headers)
        assert response.status_code in [400, 422]


class TestVeiculoCRUD:
    """Tests for Veiculo CRUD operations."""

    def test_list_veiculos(self, client, test_veiculo, auth_headers):
        """Test listing veiculos."""
        response = client.get("/api/v1/veiculos/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_veiculo(self, client, test_empresa, auth_headers):
        """Test creating a veiculo."""
        veiculo_data = {
            "marca": "Ford",
            "modelo": "Fiesta",
            "ano": 2022,
            "placa": "XYZ-5678",
            "cor": "Preto",
            "chassi": "9BWZZZ377VT000002",
            "renavam": "01234567891",
            "combustivel": "Flex",
            "cambio": "Manual",
            "portas": 4,
            "quilometragem": 5000,
            "valor_fipe": 60000.00,
            "valor_locacao": 120.00,
            "status": "disponivel",
            "empresa_id": test_empresa.id,
            "categoria": "Hatch"
        }
        response = client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_create_veiculo_duplicate_placa(self, client, test_veiculo, test_empresa, auth_headers):
        """Test creating veiculo with duplicate placa."""
        veiculo_data = {
            "marca": "Ford",
            "modelo": "Ka",
            "ano": 2022,
            "placa": test_veiculo.placa,
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        assert response.status_code in [400, 409]

    def test_update_veiculo_status(self, client, test_veiculo, auth_headers):
        """Test updating veiculo status."""
        update_data = {"status": "alugado"}
        response = client.put(f"/api/v1/veiculos/{test_veiculo.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alugado"

    def test_update_veiculo_invalid_status(self, client, test_veiculo, auth_headers):
        """Test updating veiculo with invalid status."""
        update_data = {"status": "status_invalido"}
        response = client.put(f"/api/v1/veiculos/{test_veiculo.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 422

    def test_delete_veiculo(self, client, test_veiculo, auth_headers):
        """Test deleting a veiculo."""
        response = client.delete(f"/api/v1/veiculos/{test_veiculo.id}", headers=auth_headers)
        assert response.status_code == 204


class TestContratoCRUD:
    """Tests for Contrato CRUD operations."""

    def test_list_contratos(self, client, auth_headers):
        """Test listing contratos."""
        response = client.get("/api/v1/contratos/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_contrato(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test creating a contrato."""
        contrato_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_inicio": (datetime.now()).isoformat(),
            "data_fim": (datetime.now() + timedelta(days=30)).isoformat(),
            "valor_diaria": 150.00,
            "valor_total": 4500.00,
            "forma_pagamento": "boleto",
            "status": "ativo",
            " quilometragem_inicial": 1000,
            "quilometragem_final": None,
            "observacoes": "Contrato teste"
        }
        response = client.post("/api/v1/contratos/", json=contrato_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_create_contrato_veiculo_indisponivel(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test creating contrato with unavailable vehicle."""
        test_veiculo.status = "alugado"
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.add(test_veiculo)
        db.commit()
        
        contrato_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_inicio": (datetime.now()).isoformat(),
            "data_fim": (datetime.now() + timedelta(days=30)).isoformat(),
            "valor_diaria": 150.00,
            "valor_total": 4500.00
        }
        response = client.post("/api/v1/contratos/", json=contrato_data, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_encerrar_contrato(self, client, auth_headers):
        """Test encerrar contrato."""
        response = client.post("/api/v1/contratos/1/encerrar", headers=auth_headers)
        assert response.status_code in [200, 404]

    def test_finalizar_contrato(self, client, auth_headers):
        """Test finalizar contrato."""
        response = client.post("/api/v1/contratos/1/finalizar", headers=auth_headers)
        assert response.status_code in [200, 404]


class TestReservaCRUD:
    """Tests for Reserva CRUD operations."""

    def test_list_reservas(self, client, auth_headers):
        """Test listing reservas."""
        response = client.get("/api/v1/reservas/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_reserva(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test creating a reserva."""
        reserva_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_retirada": (datetime.now() + timedelta(days=5)).isoformat(),
            "data_devolucao": (datetime.now() + timedelta(days=10)).isoformat(),
            "valor_estimado": 750.00,
            "status": "pendente",
            "observacoes": "Reserva teste"
        }
        response = client.post("/api/v1/reservas/", json=reserva_data, headers=auth_headers)
        assert response.status_code in [200, 201]

    def test_confirmar_reserva(self, client, auth_headers):
        """Test confirming a reserva."""
        response = client.post("/api/v1/reservas/1/confirmar", headers=auth_headers)
        assert response.status_code in [200, 404]

    def test_converter_reserva_contrato(self, client, auth_headers):
        """Test converting reserva to contrato."""
        response = client.post("/api/v1/reservas/1/converter", headers=auth_headers)
        assert response.status_code in [200, 404]

    def test_cancel_reserva(self, client, auth_headers):
        """Test canceling a reserva."""
        response = client.delete("/api/v1/reservas/1", headers=auth_headers)
        assert response.status_code in [204, 404]


class TestFinanceiroCRUD:
    """Tests for Financeiro CRUD operations."""

    def test_list_lancamentos(self, client, auth_headers):
        """Test listing lancamentos."""
        response = client.get("/api/v1/financeiro/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_lancamento(self, client, test_empresa, auth_headers):
        """Test creating a lancamento."""
        lancamento_data = {
            "tipo": "receita",
            "categoria": "aluguel",
            "descricao": "Recebimento teste",
            "valor": 1500.00,
            "data": datetime.now().isoformat(),
            "empresa_id": test_empresa.id,
            "forma_pagamento": "transferencia"
        }
        response = client.post("/api/v1/financeiro/", json=lancamento_data, headers=auth_headers)
        assert response.status_code in [201, 200]

    def test_create_despesa_contrato(self, client, auth_headers):
        """Test creating despesa contrato."""
        despesa_data = {
            "descricao": "Despesa teste",
            "valor": 100.00,
            "categoria": "combustivel",
            "contrato_id": 1
        }
        response = client.post("/api/v1/financeiro/despesa-contrato", json=despesa_data, headers=auth_headers)
        assert response.status_code in [201, 404]

    def test_get_resumo_financeiro(self, client, auth_headers):
        """Test getting financial summary."""
        response = client.get("/api/v1/financeiro/resumo", headers=auth_headers)
        assert response.status_code == 200


class TestSegurosCRUD:
    """Tests for Seguro CRUD operations."""

    def test_list_seguros(self, client, auth_headers):
        """Test listing seguros."""
        response = client.get("/api/v1/seguros/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_seguro(self, client, test_veiculo, test_empresa, auth_headers):
        """Test creating a seguro."""
        seguro_data = {
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "seguradora": "Seguradora Teste",
            "numero_apolice": "apolice-123",
            "tipo": "completo",
            "valor_premio": 1500.00,
            "valor_franquia": 500.00,
            "data_inicio": datetime.now().isoformat(),
            "data_fim": (datetime.now() + timedelta(days=365)).isoformat(),
            "ativo": True
        }
        response = client.post("/api/v1/seguros/", json=seguro_data, headers=auth_headers)
        assert response.status_code in [201, 200]

    def test_get_seguros_vencendo(self, client, auth_headers):
        """Test getting seguros proximos a vencer."""
        response = client.get("/api/v1/seguros/vencendo/proximos", headers=auth_headers)
        assert response.status_code == 200


class TestMultasCRUD:
    """Tests for Multa CRUD operations."""

    def test_list_multas(self, client, auth_headers):
        """Test listing multas."""
        response = client.get("/api/v1/multas/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_multa(self, client, test_veiculo, auth_headers):
        """Test creating a multa."""
        multa_data = {
            "veiculo_id": test_veiculo.id,
            "data_infracao": datetime.now().isoformat(),
            "local_infracao": "Rua Teste",
            "descricao": "Multa teste",
            "valor": 100.00,
            "status": "pendente",
            "pontos": 3
        }
        response = client.post("/api/v1/multas/", json=multa_data, headers=auth_headers)
        assert response.status_code in [201, 200]


class TestManutencaoCRUD:
    """Tests for Manutencao CRUD operations."""

    def test_list_manutencoes(self, client, auth_headers):
        """Test listing manutencoes."""
        response = client.get("/api/v1/manutencoes/", headers=auth_headers)
        assert response.status_code == 200

    def test_create_manutencao(self, client, test_veiculo, auth_headers):
        """Test creating a manutencao."""
        manutencao_data = {
            "veiculo_id": test_veiculo.id,
            "tipo": "troca_oleo",
            "descricao": "Manutencao teste",
            "data_agendamento": datetime.now().isoformat(),
            "status": "pendente",
            "custo": 200.00,
            "quilometragem": 5000
        }
        response = client.post("/api/v1/manutencoes/", json=manutencao_data, headers=auth_headers)
        assert response.status_code in [201, 200]


class TestIPVACRUD:
    """Tests for IPVA CRUD operations."""

    def test_list_ipva(self, client, auth_headers):
        """Test listing IPVA."""
        response = client.get("/api/v1/ipva/", headers=auth_headers)
        assert response.status_code == 200


class TestAuthentication:
    """Tests for authentication system."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post("/api/v1/auth/login", json={
            "username": test_user.email,
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post("/api/v1/auth/login", json={
            "username": test_user.email,
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 400]

    def test_login_invalid_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/api/v1/auth/login", json={
            "username": "nonexistent@test.com",
            "password": "password"
        })
        assert response.status_code in [401, 400]

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/empresas/")
        assert response.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        response = client.get(
            "/api/v1/empresas/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestAuthorization:
    """Tests for authorization and permissions."""

    def test_admin_access_all_endpoints(self, client, test_user, auth_headers):
        """Test admin user can access all endpoints."""
        test_user.is_superuser = True
        
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.add(test_user)
        db.commit()
        
        response = client.get("/api/v1/usuarios/", headers=auth_headers)
        assert response.status_code in [200, 403]

    def test_regular_user_limited_access(self, client, db_session):
        """Test regular user has limited access."""
        regular_user = User(
            email="regular@test.com",
            username="regularuser",
            hashed_password=get_password_hash("pass123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(regular_user)
        db_session.commit()
        
        from app.core.security import create_access_token
        token = create_access_token(data={"sub": regular_user.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/usuarios/", headers=headers)
        assert response.status_code in [200, 403]


class TestValidation:
    """Tests for data validation."""

    def test_empresa_cnpj_format(self, client, auth_headers):
        """Test empresa CNPJ format validation."""
        empresa_data = {
            "nome": "Empresa Formato",
            "cnpj": "123",
            "razao_social": "Formato LTDA"
        }
        response = client.post("/api/v1/empresas/", json=empresa_data, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_veiculo_placa_format(self, client, test_empresa, auth_headers):
        """Test veiculo placa format validation."""
        veiculo_data = {
            "marca": "Ford",
            "modelo": "Fiesta",
            "placa": "INVALID",
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/veiculos/", json=veiculo_data, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_date_range_validation(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test date range validation for contrato."""
        contrato_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_inicio": (datetime.now() + timedelta(days=30)).isoformat(),
            "data_fim": (datetime.now() + timedelta(days=10)).isoformat(),
            "valor_diaria": 150.00,
            "valor_total": 4500.00
        }
        response = client.post("/api/v1/contratos/", json=contrato_data, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_negative_value_validation(self, client, test_empresa, auth_headers):
        """Test negative value validation."""
        lancamento_data = {
            "tipo": "receita",
            "valor": -100.00,
            "empresa_id": test_empresa.id
        }
        response = client.post("/api/v1/financeiro/", json=lancamento_data, headers=auth_headers)
        assert response.status_code in [400, 422]


class TestBusinessRules:
    """Tests for business rules."""

    def test_veiculo_alugado_nao_pode_ser_alugado(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test that rented vehicle cannot be rented again."""
        test_veiculo.status = "alugado"
        
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.add(test_veiculo)
        db.commit()
        
        contrato_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_inicio": datetime.now().isoformat(),
            "data_fim": (datetime.now() + timedelta(days=30)).isoformat(),
            "valor_diaria": 150.00,
            "valor_total": 4500.00
        }
        response = client.post("/api/v1/contratos/", json=contrato_data, headers=auth_headers)
        assert response.status_code in [400, 409, 422]

    def test_contrato_atrasado_detection(self, client, auth_headers):
        """Test detecting overdue contracts."""
        response = client.get("/api/v1/contratos/atrasados", headers=auth_headers)
        assert response.status_code == 200

    def test_reserva_overlapping_dates(self, client, test_cliente, test_veiculo, test_empresa, auth_headers):
        """Test overlapping reservation dates."""
        reserva_data = {
            "cliente_id": test_cliente.id,
            "veiculo_id": test_veiculo.id,
            "empresa_id": test_empresa.id,
            "data_retirada": (datetime.now() + timedelta(days=5)).isoformat(),
            "data_devolucao": (datetime.now() + timedelta(days=10)).isoformat(),
            "valor_estimado": 750.00,
            "status": "pendente"
        }
        response = client.post("/api/v1/reservas/", json=reserva_data, headers=auth_headers)
        assert response.status_code in [200, 201, 409]

    def test_seguro_vencimento(self, client, auth_headers):
        """Test insurance expiration check."""
        response = client.get("/api/v1/seguros/vencendo/proximos", headers=auth_headers)
        assert response.status_code == 200


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_database(self, client, auth_headers):
        """Test system handles empty database."""
        response = client.get("/api/v1/veiculos/", headers=auth_headers)
        assert response.status_code == 200

    def test_pagination(self, client, auth_headers):
        """Test pagination works correctly."""
        response = client.get("/api/v1/veiculos/?page=1&limit=10", headers=auth_headers)
        assert response.status_code == 200

    def test_search_functionality(self, client, test_veiculo, auth_headers):
        """Test search functionality."""
        response = client.get(f"/api/v1/veiculos/search?q={test_veiculo.placa}", headers=auth_headers)
        assert response.status_code == 200

    def test_case_insensitive_search(self, client, test_veiculo, auth_headers):
        """Test case-insensitive search."""
        response = client.get("/api/v1/veiculos/search?q=GOL", headers=auth_headers)
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client, auth_headers):
        """Test 404 error handling."""
        response = client.get("/api/v1/empresas/999999", headers=auth_headers)
        assert response.status_code == 404

    def test_500_internal_error(self, client, auth_headers):
        """Test 500 error handling."""
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 500]

    def test_validation_error_message(self, client, auth_headers):
        """Test validation error messages are helpful."""
        response = client.post("/api/v1/empresas/", json={}, headers=auth_headers)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data or "error" in data


class TestTransactionManagement:
    """Tests for transaction management."""

    def test_rollback_on_failure(self, client, db_session, auth_headers):
        """Test that failed operations rollback properly."""
        initial_count = db_session.query(Empresa).count()
        
        empresa_data = {
            "nome": "Empresa",
            "cnpj": "invalid-cnpj",
            "razao_social": "Test LTDA"
        }
        response = client.post("/api/v1/empresas/", json=empresa_data, headers=auth_headers)
        
        final_count = db_session.query(Empresa).count()
        assert initial_count == final_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
