import math
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Cliente,
    Contrato,
    Empresa,
    UsoVeiculoEmpresa,
    Veiculo,
)

def generate_numero_contrato() -> str:
    return "CTR-{}".format(datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3])


def validar_datas(data_inicio: datetime, data_fim: datetime):
    if data_inicio >= data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data de inicio deve ser anterior a data de fim",
        )


def resolver_data_fim(
    data_inicio: datetime,
    data_fim: Optional[datetime],
    *,
    tipo: Optional[str] = None,
    vigencia_indeterminada: bool = False,
) -> Optional[datetime]:
    if data_fim:
        return data_fim

    if vigencia_indeterminada or str(tipo or "").lower() == "empresa":
        return None  # Indeterminado: data_fim fica NULL, preenchida ao encerrar

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Data final obrigatoria para contratos com prazo definido",
    )


def calcular_qtd_diarias(data_inicio: datetime, data_fim: datetime) -> int:
    total_seconds = max((data_fim - data_inicio).total_seconds(), 0)
    return max(1, math.ceil(total_seconds / 86400))


def calcular_km_excedente(
    km_inicial: Optional[float],
    km_final: Optional[float],
    km_livres: Optional[float],
) -> float:
    if km_inicial is None or km_final is None:
        return 0.0

    km_rodado = max(float(km_final) - float(km_inicial), 0.0)
    franquia = float(km_livres or 0)
    return max(km_rodado - franquia, 0.0)


def calcular_valor_total(
    data_inicio: datetime,
    data_fim: datetime,
    valor_diaria: float,
    *,
    tipo: Optional[str] = None,
    km_inicial: Optional[float] = None,
    km_final: Optional[float] = None,
    km_livres: Optional[float] = None,
    valor_km_excedente: Optional[float] = None,
    valor_avarias: Optional[float] = None,
    taxa_combustivel: Optional[float] = None,
    taxa_limpeza: Optional[float] = None,
    taxa_higienizacao: Optional[float] = None,
    taxa_pneus: Optional[float] = None,
    taxa_acessorios: Optional[float] = None,
    valor_franquia_seguro: Optional[float] = None,
    taxa_administrativa: Optional[float] = None,
    desconto: Optional[float] = None,
) -> float:
    qtd_diarias = calcular_qtd_diarias(data_inicio, data_fim)
    total_base = float(valor_diaria or 0) if str(tipo or "").lower() == "empresa" else qtd_diarias * float(valor_diaria or 0)
    km_excedente = calcular_km_excedente(km_inicial, km_final, km_livres)
    total_km = km_excedente * float(valor_km_excedente or 0)
    total_taxas = sum(
        float(valor or 0)
        for valor in (
            valor_avarias,
            taxa_combustivel,
            taxa_limpeza,
            taxa_higienizacao,
            taxa_pneus,
            taxa_acessorios,
            valor_franquia_seguro,
            taxa_administrativa,
        )
    )
    total = total_base + total_km + total_taxas - float(desconto or 0)
    return round(max(total, 0.0), 2)


def normalize_contrato_payload(payload: dict, is_create: bool = False) -> dict:
    data = dict(payload)

    if data.get("km_inicial") is None and data.get("quilometragem_inicial") is not None:
        data["km_inicial"] = data.pop("quilometragem_inicial")
    else:
        data.pop("quilometragem_inicial", None)

    if data.get("km_inicial") is None and data.get("km_atual_veiculo") is not None:
        data["km_inicial"] = data.pop("km_atual_veiculo")
    else:
        data.pop("km_atual_veiculo", None)

    if data.get("km_final") is None and data.get("quilometragem_final") is not None:
        data["km_final"] = data.pop("quilometragem_final")
    else:
        data.pop("quilometragem_final", None)

    if is_create and not data.get("numero"):
        data["numero"] = generate_numero_contrato()

    normalized = {}
    for key, value in data.items():
        if value == "":
            normalized[key] = None
        elif key in {"status", "tipo", "status_pagamento"} and isinstance(value, str):
            normalized[key] = value.lower()
        else:
            normalized[key] = value

    data_inicio = normalized.get("data_inicio")
    if isinstance(data_inicio, date) and not isinstance(data_inicio, datetime):
        normalized["data_inicio"] = datetime.combine(data_inicio, datetime.min.time())

    data_fim = normalized.get("data_fim")
    if isinstance(data_fim, date) and not isinstance(data_fim, datetime):
        normalized["data_fim"] = datetime.combine(data_fim, datetime.max.time().replace(microsecond=0))

    return normalized


def normalize_finalizacao_payload(payload: dict) -> dict:
    data = dict(payload)

    if data.get("km_final") is None and data.get("quilometragem_final") is not None:
        data["km_final"] = data.pop("quilometragem_final")
    else:
        data.pop("quilometragem_final", None)

    if data.get("km_final") is None and data.get("km_atual_veiculo") is not None:
        data["km_final"] = data.pop("km_atual_veiculo")
    else:
        data.pop("km_atual_veiculo", None)

    normalized = {}
    for key, value in data.items():
        if value == "":
            normalized[key] = None
        elif key == "status_pagamento" and isinstance(value, str):
            normalized[key] = value.lower()
        else:
            normalized[key] = value

    data_finalizacao = normalized.get("data_finalizacao")
    if isinstance(data_finalizacao, date) and not isinstance(data_finalizacao, datetime):
        normalized["data_finalizacao"] = datetime.combine(
            data_finalizacao,
            datetime.max.time().replace(microsecond=0),
        )

    return normalized


def status_pagamento_atual(contrato: Contrato) -> str:
    if contrato.status_pagamento:
        return str(contrato.status_pagamento).lower()
    if contrato.status == "finalizado":
        return "pago"
    return "pendente"


def apply_payment_details(
    contrato: Contrato,
    payment_data: dict,
    *,
    reference_date: Optional[datetime] = None,
) -> None:
    data = dict(payment_data or {})
    allowed_status = {"pendente", "pago", "cancelado"}
    current_status = status_pagamento_atual(contrato)
    next_status = current_status

    if data.get("status_pagamento"):
        next_status = str(data["status_pagamento"]).lower()
        if next_status not in allowed_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status de pagamento invalido",
            )

    if "forma_pagamento" in data:
        contrato.forma_pagamento = data.get("forma_pagamento")
    if "data_vencimento_pagamento" in data:
        contrato.data_vencimento_pagamento = data.get("data_vencimento_pagamento")
    if "data_pagamento" in data:
        contrato.data_pagamento = data.get("data_pagamento")
    if "valor_recebido" in data:
        contrato.valor_recebido = data.get("valor_recebido")

    contrato.status_pagamento = next_status
    default_due_date = (
        reference_date.date()
        if reference_date
        else contrato.data_finalizacao.date()
        if contrato.data_finalizacao
        else contrato.data_fim.date()
        if contrato.data_fim
        else datetime.now().date()
    )

    if not contrato.data_vencimento_pagamento:
        contrato.data_vencimento_pagamento = default_due_date

    if next_status == "pago":
        if not contrato.data_pagamento:
            contrato.data_pagamento = (
                reference_date.date() if reference_date else datetime.now().date()
            )
        if contrato.valor_recebido is None or float(contrato.valor_recebido or 0) <= 0:
            contrato.valor_recebido = float(contrato.valor_total or 0)
    elif next_status == "cancelado":
        if contrato.valor_recebido is None:
            contrato.valor_recebido = 0


def append_observacao(existing_value: Optional[str], extra_value: Optional[str], titulo: str) -> Optional[str]:
    if not extra_value:
        return existing_value

    extra_value = extra_value.strip()
    if not extra_value:
        return existing_value

    bloco = "[{}] {}".format(titulo, extra_value)
    if not existing_value:
        return bloco
    return "{}\n{}".format(existing_value.strip(), bloco)


def ensure_cliente_exists(db: Session, cliente_id: int) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente nao encontrado",
        )
    return cliente


def resolve_cliente_contrato(
    db: Session,
    *,
    tipo: Optional[str],
    cliente_id: Optional[int],
    empresa_id: Optional[int] = None,
) -> Cliente:
    if str(tipo or "").lower() != "empresa":
        if cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cliente obrigatorio para criar contrato",
            )
        return ensure_cliente_exists(db, cliente_id)

    target_empresa_id = empresa_id
    if not target_empresa_id and cliente_id:
        cliente_existente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente_existente and cliente_existente.empresa_id:
            return cliente_existente

        empresa_existente = db.query(Empresa).filter(Empresa.id == cliente_id).first()
        if empresa_existente:
            target_empresa_id = empresa_existente.id

    if not target_empresa_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empresa obrigatoria para criar contrato corporativo",
        )

    empresa = db.query(Empresa).filter(Empresa.id == target_empresa_id).first()
    if not empresa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )

    cliente = (
        db.query(Cliente)
        .filter(Cliente.empresa_id == target_empresa_id)
        .order_by(Cliente.id.asc())
        .first()
    )
    if cliente:
        return cliente

    cpf_base = "".join(ch for ch in str(empresa.cnpj or "") if ch.isdigit()) or f"empresa-{empresa.id}"
    cpf = cpf_base
    if db.query(Cliente).filter(Cliente.cpf == cpf).first():
        cpf = f"{cpf_base}-{empresa.id}"

    cliente = Cliente(
        nome=empresa.nome,
        cpf=cpf,
        telefone=empresa.telefone,
        email=None,
        empresa_id=empresa.id,
        ativo=True,
    )
    db.add(cliente)
    db.flush()
    return cliente


def sincronizar_uso_empresa(
    db: Session,
    contrato: Contrato,
    cliente: Cliente,
    *,
    empresa_uso_id: Optional[int] = None,
    encerrar: bool = False,
):
    empresa_id = getattr(cliente, "empresa_id", None)
    if contrato.tipo != "empresa" or not empresa_id:
        return

    uso = None
    if empresa_uso_id:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(
                UsoVeiculoEmpresa.id == empresa_uso_id,
                UsoVeiculoEmpresa.empresa_id == empresa_id,
            )
            .first()
        )
    if not uso and contrato.id:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(UsoVeiculoEmpresa.contrato_id == contrato.id)
            .first()
        )
    if not uso:
        uso = (
            db.query(UsoVeiculoEmpresa)
            .filter(
                UsoVeiculoEmpresa.empresa_id == empresa_id,
                UsoVeiculoEmpresa.veiculo_id == contrato.veiculo_id,
                UsoVeiculoEmpresa.status == "ativo",
            )
            .order_by(UsoVeiculoEmpresa.data_criacao.desc())
            .first()
        )

    if not uso:
        uso = UsoVeiculoEmpresa(
            empresa_id=empresa_id,
            veiculo_id=contrato.veiculo_id,
            status="ativo",
        )
        db.add(uso)

    uso.empresa_id = empresa_id
    uso.veiculo_id = contrato.veiculo_id
    uso.contrato_id = contrato.id
    uso.km_inicial = float(contrato.km_inicial or 0)
    uso.km_referencia = float(contrato.km_livres or 0) if contrato.km_livres is not None else uso.km_referencia
    uso.valor_km_extra = contrato.valor_km_excedente
    uso.valor_diaria_empresa = contrato.valor_diaria
    uso.data_inicio = contrato.data_inicio

    if encerrar:
        uso.km_final = float(contrato.km_final or uso.km_final or contrato.km_inicial or 0)
        if uso.km_inicial is not None and uso.km_final is not None:
            uso.km_percorrido = max(float(uso.km_final) - float(uso.km_inicial), 0.0)
        uso.data_fim = contrato.data_finalizacao or contrato.data_fim
        uso.status = "finalizado"
    else:
        uso.data_fim = None if contrato.status == "ativo" else (contrato.data_finalizacao or contrato.data_fim)
        uso.status = "ativo" if contrato.status == "ativo" else "finalizado"


def ensure_veiculo_available(
    db: Session,
    veiculo_id: int,
    contrato_id: Optional[int] = None,
) -> Veiculo:
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Veiculo nao encontrado",
        )

    contrato_ativo = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
        Contrato.id != contrato_id,
    ).first()
    if contrato_ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veiculo ja possui contrato ativo (#{})".format(contrato_ativo.numero),
        )

    if contrato_id is None and veiculo.status not in {"disponivel", "reservado"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veiculo nao esta disponivel (status atual: {})".format(veiculo.status),
        )

    return veiculo


def recalcular_status_veiculo(db: Session, veiculo_id: int):
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        return

    contratos_ativos = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
    ).count()
    veiculo.status = "alugado" if contratos_ativos > 0 else "disponivel"


