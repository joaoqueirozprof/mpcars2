import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.core.pagination import paginate
from app.models.user import User
from app.models import (
    Veiculo, DespesaVeiculo, Contrato, DespesaOperacional,
    Seguro, ParcelaSeguro, IpvaRegistro, IpvaParcela, Reserva, Multa, Manutencao,
    UsoVeiculoEmpresa, RelatorioNF, DespesaNF, Quilometragem,
    DespesaContrato, ProrrogacaoContrato, CheckinCheckout,
)
from app.services.activity_logger import log_activity


UPLOAD_DIR = "/app/uploads/veiculos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(
    prefix="/veiculos",
    tags=["Veiculos"],
    dependencies=[Depends(require_page_access("veiculos"))],
)


def _nf_total_for_uso(uso: Optional[UsoVeiculoEmpresa], relatorio: RelatorioNF) -> float:
    valor_base = float(uso.valor_diaria_empresa or 0) if uso else 0.0
    valor_extra = float(relatorio.valor_total_extra or 0)
    return round(valor_base + valor_extra, 2)


class VeiculoBase(BaseModel):
    placa: str
    marca: str
    modelo: str
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = 0
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None
    observacoes: Optional[str] = None


class VeiculoCreate(VeiculoBase):
    pass


class VeiculoUpdate(BaseModel):
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = None
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None
    status: Optional[str] = None
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


class VeiculoResponse(BaseModel):
    id: int
    placa: str
    marca: str
    modelo: str
    ano: Optional[int] = None
    cor: Optional[str] = None
    chassis: Optional[str] = None
    renavam: Optional[str] = None
    combustivel: Optional[str] = None
    capacidade_tanque: Optional[float] = None
    km_atual: Optional[float] = 0
    data_aquisicao: Optional[date] = None
    valor_aquisicao: Optional[float] = None
    status: str = "disponivel"
    foto_url: Optional[str] = None
    ativo: bool = True
    observacoes: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/")
def list_veiculos(
    page: int = 1,
    limit: int = 50,  # CORRIGIDO: era 1000, agora usa paginacao real
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicles with pagination."""
    query = db.query(Veiculo)
    return paginate(
        query=query,
        page=page,
        limit=limit,
        search=search,
        search_fields=["placa", "marca", "modelo", "cor"],
        model=Veiculo,
        status_filter=status_filter,
    )


@router.get("/search", response_model=List[VeiculoResponse])
def search_veiculos(
    q: str = "",
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search vehicles by plate, brand, or model."""
    query = db.query(Veiculo)

    if q:
        query = query.filter(
            (Veiculo.placa.ilike("%{}%".format(q)))
            | (Veiculo.marca.ilike("%{}%".format(q)))
            | (Veiculo.modelo.ilike("%{}%".format(q)))
        )

    if status:
        query = query.filter(Veiculo.status == status)

    return query.limit(100).all()


@router.get("/km/{veiculo_id}")
def get_veiculo_km(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current kilometers of a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )
    return {"veiculo_id": veiculo_id, "km_atual": veiculo.km_atual}


@router.get("/status/{veiculo_id}")
def get_veiculo_status(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get vehicle status."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )
    return {"veiculo_id": veiculo_id, "status": veiculo.status}


@router.get("/analise-financeira/{veiculo_id}")
def get_veiculo_financial_analysis(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get complete financial analysis for a vehicle.

    CORRIGIDO: Agora inclui receita de contratos, ROI, e breakdown de despesas.
    Antes so calculava despesas.
    """
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    # Receita total de contratos - SQL SUM
    contratos = db.query(Contrato).filter(Contrato.veiculo_id == veiculo_id).all()
    total_receita_contratos = sum(
        float(contrato.valor_total or 0)
        for contrato in contratos
        if str(contrato.tipo or "").lower() != "empresa"
    )
    relatorios_nf = db.query(RelatorioNF).filter(RelatorioNF.veiculo_id == veiculo_id).all()
    uso_ids = [relatorio.uso_id for relatorio in relatorios_nf if relatorio.uso_id]
    usos_empresa = {}
    if uso_ids:
        for uso in db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id.in_(uso_ids)).all():
            usos_empresa[uso.id] = uso
    total_receita_nf = sum(
        _nf_total_for_uso(usos_empresa.get(relatorio.uso_id), relatorio)
        for relatorio in relatorios_nf
    )
    total_receita = total_receita_contratos + total_receita_nf

    # Total de contratos
    total_contratos = len(contratos)

    # Despesas do veiculo - SQL SUM
    total_despesas_veiculo = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaVeiculo.valor), 0)
    ).filter(DespesaVeiculo.veiculo_id == veiculo_id).scalar())

    # Despesas de contratos do veiculo
    total_despesas_contrato = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(DespesaContrato.valor), 0)
    ).join(Contrato, Contrato.id == DespesaContrato.contrato_id).filter(
        Contrato.veiculo_id == veiculo_id
    ).scalar())

    # Custos com multas
    total_multas = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Multa.valor), 0)
    ).filter(Multa.veiculo_id == veiculo_id).scalar())

    # Custos com manutencao
    total_manutencao = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Manutencao.custo), 0)
    ).filter(Manutencao.veiculo_id == veiculo_id).scalar())

    # Custos com seguros
    total_seguros = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(Seguro.valor), 0)
    ).filter(Seguro.veiculo_id == veiculo_id).scalar())

    # Custos com IPVA
    total_ipva = float(db.query(
        sqlfunc.coalesce(sqlfunc.sum(IpvaRegistro.valor), 0)
    ).filter(IpvaRegistro.veiculo_id == veiculo_id).scalar())

    # Totais
    total_despesas = (
        total_despesas_veiculo + total_despesas_contrato + total_multas +
        total_manutencao + total_seguros + total_ipva
    )
    lucro_liquido = total_receita - total_despesas
    valor_aquisicao = float(veiculo.valor_aquisicao) if veiculo.valor_aquisicao else 0

    # ROI = (lucro_liquido / investimento) * 100
    roi = round((lucro_liquido / valor_aquisicao * 100), 1) if valor_aquisicao > 0 else 0

    return {
        "veiculo_id": veiculo_id,
        "placa": veiculo.placa,
        "marca_modelo": "{} {}".format(veiculo.marca, veiculo.modelo),
        "valor_aquisicao": valor_aquisicao,
        "total_receita": total_receita,
        "total_contratos": total_contratos,
        "receita_nf_empresa": total_receita_nf,
        "despesas": {
            "veiculo": total_despesas_veiculo,
            "contrato": total_despesas_contrato,
            "multas": total_multas,
            "manutencao": total_manutencao,
            "seguros": total_seguros,
            "ipva": total_ipva,
        },
        "total_despesas": total_despesas,
        "lucro_liquido": lucro_liquido,
        "roi_percentual": roi,
    }


@router.get("/historico-financeiro/{veiculo_id}")
def get_veiculo_financial_history(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the complete financial history for a vehicle."""
    del current_user
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    records = []

    if veiculo.valor_aquisicao:
        records.append(
            {
                "id": "aq-{}".format(veiculo.id),
                "data": veiculo.data_aquisicao.isoformat() if veiculo.data_aquisicao else None,
                "tipo": "despesa",
                "categoria": "Aquisicao",
                "descricao": "Compra do veiculo {}".format(veiculo.placa),
                "valor": float(veiculo.valor_aquisicao),
                "origem_tipo": "aquisicao",
            }
        )

    contratos = db.query(Contrato).filter(Contrato.veiculo_id == veiculo_id).all()
    for contrato in contratos:
        if str(contrato.tipo or "").lower() == "empresa":
            continue
        records.append(
            {
                "id": "ct-{}".format(contrato.id),
                "data": contrato.data_finalizacao.isoformat() if contrato.data_finalizacao else contrato.data_criacao.isoformat() if contrato.data_criacao else None,
                "tipo": "receita",
                "categoria": "Contrato",
                "descricao": "Contrato {}".format(contrato.numero),
                "valor": float(contrato.valor_total or 0),
                "origem_tipo": "contrato",
            }
        )

    relatorios_nf = db.query(RelatorioNF).filter(RelatorioNF.veiculo_id == veiculo_id).all()
    uso_ids = [relatorio.uso_id for relatorio in relatorios_nf if relatorio.uso_id]
    usos_empresa = {}
    if uso_ids:
        for uso in db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id.in_(uso_ids)).all():
            usos_empresa[uso.id] = uso
    for relatorio in relatorios_nf:
        uso = usos_empresa.get(relatorio.uso_id)
        periodo_inicio = relatorio.periodo_inicio.strftime("%d/%m/%Y") if relatorio.periodo_inicio else "-"
        periodo_fim = relatorio.periodo_fim.strftime("%d/%m/%Y") if relatorio.periodo_fim else "-"
        records.append(
            {
                "id": "nf-{}".format(relatorio.id),
                "data": relatorio.periodo_fim.isoformat() if relatorio.periodo_fim else relatorio.data_criacao.isoformat() if relatorio.data_criacao else None,
                "tipo": "receita",
                "categoria": "Faturamento empresa",
                "descricao": "Periodo {} a {}".format(periodo_inicio, periodo_fim),
                "valor": _nf_total_for_uso(uso, relatorio),
                "origem_tipo": "nf_empresa",
            }
        )

    for despesa in db.query(DespesaVeiculo).filter(DespesaVeiculo.veiculo_id == veiculo_id).all():
        records.append(
            {
                "id": "dv-{}".format(despesa.id),
                "data": despesa.data.isoformat() if despesa.data else None,
                "tipo": "despesa",
                "categoria": despesa.tipo or "Despesa veiculo",
                "descricao": despesa.descricao,
                "valor": float(despesa.valor or 0),
                "origem_tipo": "despesa_veiculo",
            }
        )

    for despesa in (
        db.query(DespesaContrato)
        .join(Contrato, Contrato.id == DespesaContrato.contrato_id)
        .filter(Contrato.veiculo_id == veiculo_id)
        .all()
    ):
        records.append(
            {
                "id": "dc-{}".format(despesa.id),
                "data": despesa.data_registro.isoformat() if despesa.data_registro else None,
                "tipo": "despesa",
                "categoria": despesa.tipo or "Despesa contrato",
                "descricao": despesa.descricao,
                "valor": float(despesa.valor or 0),
                "origem_tipo": "despesa_contrato",
            }
        )

    for manutencao in db.query(Manutencao).filter(Manutencao.veiculo_id == veiculo_id).all():
        records.append(
            {
                "id": "mt-{}".format(manutencao.id),
                "data": manutencao.data_realizada.isoformat() if manutencao.data_realizada else manutencao.data_criacao.isoformat() if manutencao.data_criacao else None,
                "tipo": "despesa",
                "categoria": "Manutencao / {}".format(manutencao.tipo),
                "descricao": manutencao.descricao,
                "valor": float(manutencao.custo or 0),
                "origem_tipo": "manutencao",
            }
        )

    for seguro in db.query(Seguro).filter(Seguro.veiculo_id == veiculo_id).all():
        records.append(
            {
                "id": "sg-{}".format(seguro.id),
                "data": seguro.data_inicio.isoformat() if seguro.data_inicio else None,
                "tipo": "despesa",
                "categoria": "Seguro",
                "descricao": "{} - {}".format(seguro.seguradora or "Seguro", seguro.numero_apolice or "sem apolice"),
                "valor": float(seguro.valor or 0),
                "origem_tipo": "seguro",
            }
        )

    for ipva in db.query(IpvaRegistro).filter(IpvaRegistro.veiculo_id == veiculo_id).all():
        records.append(
            {
                "id": "ip-{}".format(ipva.id),
                "data": ipva.data_pagamento.isoformat() if ipva.data_pagamento else ipva.data_vencimento.isoformat() if ipva.data_vencimento else None,
                "tipo": "despesa",
                "categoria": "IPVA",
                "descricao": "IPVA {}".format(ipva.ano_referencia or ""),
                "valor": float(ipva.valor_ipva or ipva.valor_pago or 0),
                "origem_tipo": "ipva",
            }
        )

    for multa in db.query(Multa).filter(Multa.veiculo_id == veiculo_id).all():
        records.append(
            {
                "id": "ml-{}".format(multa.id),
                "data": multa.data_pagamento.isoformat() if multa.data_pagamento else multa.data_infracao.isoformat() if multa.data_infracao else None,
                "tipo": "despesa",
                "categoria": "Multa",
                "descricao": multa.descricao or "Multa",
                "valor": float(multa.valor or 0),
                "origem_tipo": "multa",
            }
        )

    records.sort(key=lambda item: item.get("data") or "", reverse=True)

    total_receita = sum(item["valor"] for item in records if item["tipo"] == "receita")
    total_despesa = sum(item["valor"] for item in records if item["tipo"] == "despesa")

    return {
        "veiculo_id": veiculo.id,
        "placa": veiculo.placa,
        "veiculo": "{} {}".format(veiculo.marca, veiculo.modelo),
        "total_receita": total_receita,
        "total_despesa": total_despesa,
        "saldo": total_receita - total_despesa,
        "records": records,
    }


@router.get("/foto/{veiculo_id}")
def get_veiculo_foto(
    veiculo_id: int,
    db: Session = Depends(get_db),
):
    """Serve vehicle photo file."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo or not veiculo.foto_url:
        raise HTTPException(status_code=404, detail="Foto nao encontrada")

    file_path = os.path.join(UPLOAD_DIR, veiculo.foto_url)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo de foto nao encontrado")

    return FileResponse(file_path)


@router.post("/{veiculo_id}/foto")
async def upload_veiculo_foto(
    veiculo_id: int,
    foto: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Upload a photo for a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if foto.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de arquivo nao permitido. Use JPEG, PNG, WebP ou GIF.",
        )

    contents = await foto.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo muito grande. Maximo 10MB.",
        )

    if veiculo.foto_url:
        old_path = os.path.join(UPLOAD_DIR, veiculo.foto_url)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = os.path.splitext(foto.filename or "photo.jpg")[1] or ".jpg"
    filename = "veiculo_{}_{}{}".format(veiculo_id, uuid.uuid4().hex[:8], ext)
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    veiculo.foto_url = filename
    db.commit()
    db.refresh(veiculo)
    log_activity(db, current_user, "EDITAR", "Veiculo", "Foto do veiculo {} atualizada".format(veiculo.placa), veiculo_id, request)

    return {
        "message": "Foto enviada com sucesso",
        "foto_url": filename,
        "veiculo_id": veiculo_id,
    }


@router.delete("/{veiculo_id}/foto")
def delete_veiculo_foto(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a vehicle photo."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    if veiculo.foto_url:
        file_path = os.path.join(UPLOAD_DIR, veiculo.foto_url)
        if os.path.exists(file_path):
            os.remove(file_path)
        veiculo.foto_url = None
        db.commit()
        log_activity(db, current_user, "EXCLUIR", "Veiculo", "Foto do veiculo {} removida".format(veiculo.placa), veiculo_id, request)

    return {"message": "Foto removida com sucesso"}


@router.post("/", response_model=VeiculoResponse)
def create_veiculo(
    veiculo: VeiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create a new vehicle."""
    existing = db.query(Veiculo).filter(Veiculo.placa == veiculo.placa).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Placa ja cadastrada"
        )

    db_veiculo = Veiculo(**veiculo.model_dump())
    db.add(db_veiculo)
    db.commit()
    db.refresh(db_veiculo)
    log_activity(db, current_user, "CRIAR", "Veiculo", "Veiculo {} criado".format(db_veiculo.placa), db_veiculo.id, request)
    return db_veiculo


@router.get("/{veiculo_id}", response_model=VeiculoResponse)
def get_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )
    return veiculo


@router.put("/{veiculo_id}", response_model=VeiculoResponse)
def update_veiculo(
    veiculo_id: int,
    veiculo_data: VeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Update a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    update_data = veiculo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(veiculo, key, value)

    db.commit()
    db.refresh(veiculo)
    log_activity(db, current_user, "EDITAR", "Veiculo", "Veiculo {} editado".format(veiculo.placa), veiculo_id, request)
    return veiculo


@router.patch("/{veiculo_id}", response_model=VeiculoResponse)
def patch_veiculo(
    veiculo_id: int,
    veiculo_data: VeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Partially update a vehicle."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    update_data = veiculo_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(veiculo, key, value)

    db.commit()
    db.refresh(veiculo)
    log_activity(db, current_user, "EDITAR", "Veiculo", "Veiculo {} editado".format(veiculo.placa), veiculo_id, request)
    return veiculo


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_veiculo(
    veiculo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Delete a vehicle and all related records without relying on DB cascades."""
    veiculo = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
    if not veiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Veiculo nao encontrado"
        )

    # Verificar se tem contratos ativos
    contratos_ativos = db.query(Contrato).filter(
        Contrato.veiculo_id == veiculo_id,
        Contrato.status == "ativo",
    ).count()
    if contratos_ativos > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nao e possivel excluir veiculo com {} contrato(s) ativo(s). Finalize-os primeiro.".format(contratos_ativos),
        )

    # Delete photo file if exists
    if veiculo.foto_url:
        file_path = os.path.join(UPLOAD_DIR, veiculo.foto_url)
        if os.path.exists(file_path):
            os.remove(file_path)

    contrato_ids = [
        contrato_id
        for (contrato_id,) in db.query(Contrato.id).filter(Contrato.veiculo_id == veiculo_id).all()
    ]
    if contrato_ids:
        db.query(Quilometragem).filter(
            Quilometragem.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(DespesaContrato).filter(
            DespesaContrato.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(ProrrogacaoContrato).filter(
            ProrrogacaoContrato.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(CheckinCheckout).filter(
            CheckinCheckout.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(UsoVeiculoEmpresa).filter(
            UsoVeiculoEmpresa.contrato_id.in_(contrato_ids)
        ).update({UsoVeiculoEmpresa.contrato_id: None}, synchronize_session=False)
        db.query(Multa).filter(
            Multa.contrato_id.in_(contrato_ids)
        ).delete(synchronize_session=False)
        db.query(Contrato).filter(
            Contrato.id.in_(contrato_ids)
        ).delete(synchronize_session=False)

    seguro_ids = [
        seguro_id
        for (seguro_id,) in db.query(Seguro.id).filter(Seguro.veiculo_id == veiculo_id).all()
    ]
    if seguro_ids:
        db.query(ParcelaSeguro).filter(
            ParcelaSeguro.seguro_id.in_(seguro_ids)
        ).delete(synchronize_session=False)

    ipva_ids = [
        ipva_id
        for (ipva_id,) in db.query(IpvaRegistro.id).filter(IpvaRegistro.veiculo_id == veiculo_id).all()
    ]
    if ipva_ids:
        db.query(IpvaParcela).filter(
            IpvaParcela.ipva_id.in_(ipva_ids)
        ).delete(synchronize_session=False)

    uso_ids = [
        uso_id
        for (uso_id,) in db.query(UsoVeiculoEmpresa.id).filter(UsoVeiculoEmpresa.veiculo_id == veiculo_id).all()
    ]
    if uso_ids:
        db.query(RelatorioNF).filter(
            RelatorioNF.uso_id.in_(uso_ids)
        ).delete(synchronize_session=False)

    db.query(DespesaOperacional).filter(DespesaOperacional.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(DespesaVeiculo).filter(DespesaVeiculo.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(ParcelaSeguro).filter(ParcelaSeguro.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(Seguro).filter(Seguro.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(IpvaParcela).filter(IpvaParcela.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(IpvaRegistro).filter(IpvaRegistro.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(Reserva).filter(Reserva.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(Multa).filter(Multa.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(Manutencao).filter(Manutencao.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(DespesaNF).filter(DespesaNF.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(RelatorioNF).filter(RelatorioNF.veiculo_id == veiculo_id).delete(synchronize_session=False)
    db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.veiculo_id == veiculo_id).delete(synchronize_session=False)

    placa = veiculo.placa
    db.delete(veiculo)
    db.commit()
    log_activity(db, current_user, "EXCLUIR", "Veiculo", "Veiculo {} excluido".format(placa), veiculo_id, request)
