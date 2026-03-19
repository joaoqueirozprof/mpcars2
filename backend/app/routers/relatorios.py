import os
"""Routers de relatórios - versão limpa.

CORRIGIDO: Removidas rotas legacy duplicadas que faziam a mesma coisa
que as rotas spec (/exportar/*). As rotas spec unificadas já suportam
CSV e XLSX com filtros, tornando as rotas legacy redundantes.

Rotas legacy removidas:
- /contratos/pdf -> usar /financeiro/pdf (mais completo)
- /receitas/pdf -> coberto por /financeiro/pdf
- /despesas/pdf -> coberto por /financeiro/pdf
- /frota/pdf -> coberto por /exportar/veiculos
- /clientes/pdf -> coberto por /exportar/clientes
- /ipva/pdf -> funcionalidade única, MANTIDA como /ipva/pdf
- /contratos/xlsx -> usar /exportar/contratos?formato=xlsx
- /contratos/csv -> usar /exportar/contratos?formato=csv
- /veiculos/xlsx -> usar /exportar/veiculos?formato=xlsx
- /clientes/xlsx -> usar /exportar/clientes?formato=xlsx
- /despesas/xlsx -> usar /exportar/financeiro?formato=xlsx
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.models.user import User
from app.models import Contrato, RelatorioNF, UsoVeiculoEmpresa, Empresa, Veiculo, PagamentoNF
from app.services.pdf_service import PDFService
from app.services.pdf_contrato import PDFContratoService
from app.services.pdf_financeiro import PDFFinanceiroService
from app.services.pdf_nf import PDFNFService
from app.services.exportacao import ExportacaoService


router = APIRouter(
    prefix="/relatorios",
    tags=["Relatorios"],
    dependencies=[Depends(require_page_access("relatorios"))],
)


def _resolve_nf_period(periodo_inicio: Optional[date], periodo_fim: Optional[date]) -> tuple[date, date]:
    today = date.today()
    start = periodo_inicio or (periodo_fim.replace(day=1) if periodo_fim else today.replace(day=1))
    end = periodo_fim or today

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="periodo_inicio deve ser menor ou igual a periodo_fim.",
        )

    return start, end


def _upsert_relatorio_nf(
    db: Session,
    *,
    uso: UsoVeiculoEmpresa,
    periodo_inicio: date,
    periodo_fim: date,
    km_percorrido: float,
    km_referencia: Optional[float] = None,
    valor_km_extra: Optional[float] = None,
) -> RelatorioNF:
    km_real = float(km_percorrido or 0)
    km_permitido = float(km_referencia if km_referencia is not None else (uso.km_referencia or 0))
    taxa_extra = float(valor_km_extra if valor_km_extra is not None else (uso.valor_km_extra or 0))
    km_excedente = max(km_real - km_permitido, 0.0)
    valor_total_extra = km_excedente * taxa_extra

    uso.km_percorrido = km_real
    if km_referencia is not None:
        uso.km_referencia = km_referencia
    if valor_km_extra is not None:
        uso.valor_km_extra = valor_km_extra

    # Always create a new record to keep full history of all NF periods
    _valor_diaria = float(uso.valor_diaria_empresa or 0)
    _valor_total_periodo = _valor_diaria + valor_total_extra

    relatorio = RelatorioNF(
        veiculo_id=uso.veiculo_id,
        empresa_id=uso.empresa_id,
        uso_id=uso.id,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        km_percorrida=km_real,
        km_excedente=km_excedente,
        valor_total_extra=valor_total_extra,
        valor_diaria=_valor_diaria,
        valor_total_periodo=_valor_total_periodo,
    )
    db.add(relatorio)
    return relatorio


def _parse_optional_export_dates(
    data_inicio: Optional[str],
    data_fim: Optional[str],
) -> tuple[Optional[date], Optional[date]]:
    parsed_start = None
    parsed_end = None

    if data_inicio:
        try:
            parsed_start = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data_inicio invalida. Use o formato YYYY-MM-DD.",
            ) from exc

    if data_fim:
        try:
            parsed_end = datetime.strptime(data_fim, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="data_fim invalida. Use o formato YYYY-MM-DD.",
            ) from exc

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="data_inicio deve ser menor ou igual a data_fim.",
        )

    return parsed_start, parsed_end


# ============================================================
# PDF 1 - CONTRATO DE LOCAÇÃO
# ============================================================
@router.get("/contrato/{contrato_id}/pdf")
def get_contrato_pdf(
    contrato_id: int,
    veiculo_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate contract PDF report (uses original layout matching physical form).
    
    Args:
        contrato_id: ID do contrato
        veiculo_id: ID opcional do veículo para gerar o PDF com dados específicos
                    (útil para contratos de empresa com múltiplos veículos)
    """
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato nao encontrado")

    if not contrato.cliente_id or not contrato.veiculo_id:
        raise HTTPException(status_code=422, detail="Contrato com dados incompletos (cliente ou veiculo ausente)")

    # Use the provided veiculo_id if different from contract's main vehicle
    target_veiculo_id = veiculo_id if veiculo_id else contrato.veiculo_id
    veiculo = db.query(Veiculo).filter(Veiculo.id == target_veiculo_id).first()
    placa = veiculo.placa if veiculo else "000"
    data_str = datetime.now().strftime("%Y%m%d")

    try:
        pdf_buffer = PDFService.generate_contrato_pdf(db, contrato_id, veiculo_id=target_veiculo_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF do contrato: {}".format(str(e)))

    # Include vehicle info in filename if different from contract's main vehicle
    filename_suffix = ""
    if veiculo_id and veiculo_id != contrato.veiculo_id:
        filename_suffix = f"_{placa}"
    
    filename = "contrato_{}{}_{}".format(contrato_id, filename_suffix, data_str)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="{}.pdf"'.format(filename)},
    )


# ============================================================
# PDF 2 - RELATÓRIO FINANCEIRO
# ============================================================
@router.get("/financeiro/pdf")
def get_financeiro_pdf(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate financial report PDF (spec-compliant 4 sections)."""
    try:
        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de data invalido")

    if di > df:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="data_inicio deve ser menor ou igual a data_fim")

    try:
        pdf_buffer = PDFFinanceiroService.generate_relatorio_financeiro_pdf(db, data_inicio, data_fim)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar relatorio financeiro: {}".format(str(e)))

    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="relatorio_financeiro_{}_{}.pdf"'.format(data_inicio, data_fim)},
    )


# ============================================================
# PDF 3 - NOTA FISCAL DE USO (single vehicle)
# ============================================================
@router.get("/nf/{uso_id}/pdf")
@router.post("/nf/{uso_id}/pdf")
def get_nf_pdf(
    uso_id: int,
    km_percorrido: Optional[float] = None,
    km_referencia: Optional[float] = None,
    valor_km_extra: Optional[float] = None,
    periodo_inicio: Optional[str] = None,
    periodo_fim: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate NF PDF for a single vehicle usage."""
    uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
    if not uso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uso de veiculo nao encontrado")

    empresa = db.query(Empresa).filter(Empresa.id == uso.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa nao encontrada para este uso")

    parsed_start, parsed_end = _parse_optional_export_dates(periodo_inicio, periodo_fim)
    billing_start, billing_end = _resolve_nf_period(parsed_start, parsed_end)

    if km_percorrido is not None:
        _upsert_relatorio_nf(
            db,
            uso=uso,
            periodo_inicio=billing_start,
            periodo_fim=billing_end,
            km_percorrido=km_percorrido,
            km_referencia=km_referencia,
            valor_km_extra=valor_km_extra,
        )
        db.commit()

    try:
        pdf_buffer = PDFNFService.generate_nf_pdf(
            db, uso_id, km_percorrido,
            km_referencia_override=km_referencia,
            valor_km_extra_override=valor_km_extra
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar NF: {}".format(str(e)))

    cnpj_clean = (empresa.cnpj or "").replace(".", "").replace("/", "").replace("-", "")
    mes_ano = datetime.now().strftime("%m_%Y")
    veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
    placa = (veiculo.placa or "000") if veiculo else "000"
    filename = "nf_{}_{}_{}.pdf".format(placa, cnpj_clean, mes_ano)

    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.get("/nf/historico")
def list_all_nf(
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all NF records with company and vehicle info."""
    query = db.query(RelatorioNF).order_by(RelatorioNF.data_criacao.desc())
    if empresa_id:
        query = query.filter(RelatorioNF.empresa_id == empresa_id)
    registros = query.limit(200).all()

    result = []
    for r in registros:
        empresa = db.query(Empresa).filter(Empresa.id == r.empresa_id).first()
        veiculo = db.query(Veiculo).filter(Veiculo.id == r.veiculo_id).first()
        result.append({
            "id": r.id,
            "empresa_nome": empresa.nome if empresa else "",
            "empresa_cnpj": empresa.cnpj if empresa else "",
            "veiculo_placa": veiculo.placa if veiculo else "",
            "veiculo_modelo": "{} {}".format(veiculo.marca, veiculo.modelo) if veiculo else "",
            "periodo_inicio": r.periodo_inicio.isoformat() if r.periodo_inicio else None,
            "periodo_fim": r.periodo_fim.isoformat() if r.periodo_fim else None,
            "km_percorrida": r.km_percorrida,
            "km_excedente": r.km_excedente,
            "valor_total_extra": float(r.valor_total_extra or 0),
            "valor_diaria": float(r.valor_diaria or 0),
            "valor_total_periodo": float(r.valor_total_periodo or 0),
            "pago": bool(r.pago),
            "data_pagamento": r.data_pagamento.isoformat() if r.data_pagamento else None,
            "forma_pagamento": r.forma_pagamento,
            "comprovante_url": r.comprovante_url,
            "data_criacao": r.data_criacao.isoformat() if r.data_criacao else None,
        })
    return result


@router.get("/nf/{nf_id}/comprovante")
def get_nf_comprovante(
    nf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download/view the payment receipt for an NF."""
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not nf or not nf.comprovante_url:
        raise HTTPException(status_code=404, detail="Comprovante nao encontrado")
    safe_path = os.path.basename(nf.comprovante_url or "")
    filepath = os.path.join("/app/uploads/comprovantes", safe_path)
    if not safe_path or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
    import mimetypes
    media_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    return FileResponse(filepath, media_type=media_type, filename=os.path.basename(filepath))


@router.delete("/nf/{nf_id}/comprovante")
def delete_nf_comprovante(
    nf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the payment receipt for an NF."""
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not nf:
        raise HTTPException(status_code=404, detail="NF nao encontrada")
    if nf.comprovante_url:
        filepath = "/app" + nf.comprovante_url
        if os.path.exists(filepath):
            os.remove(filepath)
    nf.comprovante_url = None
    db.commit()
    return {"id": nf.id, "comprovante_url": None}


@router.patch("/nf/{nf_id}/pagamento")
def update_nf_pagamento(
    nf_id: int,
    pago: bool,
    data_pagamento: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an NF period as paid or unpaid."""
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not nf:
        raise HTTPException(status_code=404, detail="NF nao encontrada")
    nf.pago = pago
    if pago and data_pagamento:
        from datetime import datetime as dt
        try:
            nf.data_pagamento = dt.strptime(data_pagamento, "%Y-%m-%d").date()
        except ValueError:
            nf.data_pagamento = dt.now().date()
    elif pago and not nf.data_pagamento:
        from datetime import datetime as dt
        nf.data_pagamento = dt.now().date()
    if forma_pagamento is not None:
        nf.forma_pagamento = forma_pagamento
    if not pago:
        nf.data_pagamento = None
        nf.forma_pagamento = None
    db.commit()
    return {"id": nf.id, "pago": nf.pago, "data_pagamento": str(nf.data_pagamento) if nf.data_pagamento else None, "forma_pagamento": nf.forma_pagamento}


@router.post("/nf/{nf_id}/comprovante")
def upload_nf_comprovante(
    nf_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload payment receipt for an NF period."""
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not nf:
        raise HTTPException(status_code=404, detail="NF nao encontrada")
    upload_dir = "/app/uploads/comprovantes"
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(arquivo.filename or "")[1] or ".pdf"
    filename = "comprovante_nf_{}{}".format(nf_id, ext)
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(arquivo.file.read())
    nf.comprovante_url = "/uploads/comprovantes/{}".format(filename)
    db.commit()
    return {"id": nf.id, "comprovante_url": nf.comprovante_url}


@router.get("/nf/{nf_id}/pagamentos")
def list_nf_pagamentos(
    nf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all payments for an NF period."""
    pagamentos = db.query(PagamentoNF).filter(PagamentoNF.relatorio_nf_id == nf_id).order_by(PagamentoNF.data_criacao.desc()).all()
    return [{
        "id": p.id,
        "valor": float(p.valor or 0),
        "data_pagamento": p.data_pagamento.isoformat() if p.data_pagamento else None,
        "forma_pagamento": p.forma_pagamento,
        "comprovante_url": p.comprovante_url,
        "observacao": p.observacao,
        "data_criacao": p.data_criacao.isoformat() if p.data_criacao else None,
    } for p in pagamentos]


@router.post("/nf/{nf_id}/pagamentos")
def add_nf_pagamento(
    nf_id: int,
    valor: float,
    data_pagamento: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    observacao: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a payment to an NF period (supports partial payments)."""
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not nf:
        raise HTTPException(status_code=404, detail="NF nao encontrada")
    if valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo")

    from datetime import datetime as dt
    dp = None
    if data_pagamento:
        try:
            dp = dt.strptime(data_pagamento, "%Y-%m-%d").date()
        except ValueError:
            dp = dt.now().date()
    else:
        dp = dt.now().date()

    pagamento = PagamentoNF(
        relatorio_nf_id=nf_id,
        valor=valor,
        data_pagamento=dp,
        forma_pagamento=forma_pagamento,
        observacao=observacao,
    )
    db.add(pagamento)

    # Auto-update NF pago status based on total payments
    total_pago = sum(float(p.valor or 0) for p in db.query(PagamentoNF).filter(PagamentoNF.relatorio_nf_id == nf_id).all()) + valor
    total_periodo = float(nf.valor_total_periodo or 0)
    nf.pago = total_pago + 0.01 >= total_periodo
    nf.data_pagamento = dp
    nf.forma_pagamento = forma_pagamento

    db.commit()
    db.refresh(pagamento)
    return {
        "id": pagamento.id,
        "valor": float(pagamento.valor),
        "total_pago": total_pago,
        "total_periodo": total_periodo,
        "status": "pago" if nf.pago else "parcial",
    }


@router.delete("/nf/pagamentos/{pagamento_id}")
def delete_nf_pagamento(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a payment record."""
    pagamento = db.query(PagamentoNF).filter(PagamentoNF.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento nao encontrado")
    nf_id = pagamento.relatorio_nf_id
    db.delete(pagamento)
    # Recalculate NF status
    nf = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if nf:
        total_pago = sum(float(p.valor or 0) for p in db.query(PagamentoNF).filter(PagamentoNF.relatorio_nf_id == nf_id).all())
        nf.pago = total_pago + 0.01 >= float(nf.valor_total_periodo or 0)
        if total_pago <= 0:
            nf.pago = False
            nf.data_pagamento = None
    db.commit()
    return {"status": "deleted"}


@router.post("/nf/pagamentos/{pagamento_id}/comprovante")
def upload_pagamento_comprovante(
    pagamento_id: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload receipt for a specific payment."""
    pagamento = db.query(PagamentoNF).filter(PagamentoNF.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento nao encontrado")
    upload_dir = "/app/uploads/comprovantes"
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(arquivo.filename or "")[1] or ".pdf"
    filename = "comprovante_pgto_{}{}".format(pagamento_id, ext)
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(arquivo.file.read())
    pagamento.comprovante_url = "/uploads/comprovantes/{}".format(filename)
    db.commit()
    return {"id": pagamento.id, "comprovante_url": pagamento.comprovante_url}


@router.get("/nf/reprint/{nf_id}")
def reprint_nf_pdf(
    nf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reprint a previously generated NF PDF by its record ID."""
    relatorio = db.query(RelatorioNF).filter(RelatorioNF.id == nf_id).first()
    if not relatorio:
        raise HTTPException(status_code=404, detail="Relatorio NF nao encontrado")

    uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == relatorio.uso_id).first()
    empresa = db.query(Empresa).filter(Empresa.id == relatorio.empresa_id).first()

    try:
        pdf_buffer = PDFNFService.generate_nf_pdf(
            db, relatorio.uso_id, float(relatorio.km_percorrida or 0),
            km_referencia_override=float(uso.km_referencia or 0) if uso else None,
            valor_km_extra_override=float(uso.valor_km_extra or 0) if uso else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar NF: {}".format(str(e)))

    cnpj = (empresa.cnpj or "").replace(".", "").replace("/", "").replace("-", "") if empresa else "000"
    periodo = ""
    if relatorio.periodo_inicio and relatorio.periodo_fim:
        periodo = "{}_a_{}".format(
            relatorio.periodo_inicio.strftime("%d%m%Y"),
            relatorio.periodo_fim.strftime("%d%m%Y"),
        )
    veiculo = db.query(Veiculo).filter(Veiculo.id == relatorio.veiculo_id).first()
    placa = (veiculo.placa or "000") if veiculo else "000"
    filename = "nf_{}_{}{}.pdf".format(placa, cnpj, "_" + periodo if periodo else "")

    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.get("/nf/{uso_id}/historico")
def get_nf_historico(
    uso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all NF records (history) for a vehicle usage."""
    registros = (
        db.query(RelatorioNF)
        .filter(RelatorioNF.uso_id == uso_id)
        .order_by(RelatorioNF.data_criacao.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "periodo_inicio": r.periodo_inicio.isoformat() if r.periodo_inicio else None,
            "periodo_fim": r.periodo_fim.isoformat() if r.periodo_fim else None,
            "km_percorrida": r.km_percorrida,
            "km_excedente": r.km_excedente,
            "valor_total_extra": float(r.valor_total_extra or 0),
            "valor_diaria": float(r.valor_diaria or 0),
            "valor_total_periodo": float(r.valor_total_periodo or 0),
            "pago": bool(r.pago),
            "data_pagamento": r.data_pagamento.isoformat() if r.data_pagamento else None,
            "forma_pagamento": r.forma_pagamento,
            "comprovante_url": r.comprovante_url,
            "data_criacao": r.data_criacao.isoformat() if r.data_criacao else None,
        }
        for r in registros
    ]


# ============================================================
# PDF 3B - NF CONSOLIDADA (múltiplos veículos de uma empresa)
# ============================================================
from pydantic import BaseModel as PydanticBase
from typing import List as TypingList


class VeiculoKM(PydanticBase):
    uso_id: int
    km_percorrido: float
    km_referencia: Optional[float] = None
    valor_km_extra: Optional[float] = None


class NFEmpresaRequest(PydanticBase):
    empresa_id: int
    veiculos: TypingList[VeiculoKM]
    periodo_inicio: Optional[date] = None
    periodo_fim: Optional[date] = None


@router.post("/nf/empresa/pdf")
def get_nf_empresa_pdf(
    request: NFEmpresaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate consolidated NF PDF for multiple vehicles of a company."""
    empresa = db.query(Empresa).filter(Empresa.id == request.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")

    if not request.veiculos:
        raise HTTPException(status_code=400, detail="Nenhum veiculo informado")

    billing_start, billing_end = _resolve_nf_period(request.periodo_inicio, request.periodo_fim)

    for item in request.veiculos:
        uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == item.uso_id).first()
        if uso:
            _upsert_relatorio_nf(
                db,
                uso=uso,
                periodo_inicio=billing_start,
                periodo_fim=billing_end,
                km_percorrido=item.km_percorrido,
                km_referencia=item.km_referencia,
                valor_km_extra=item.valor_km_extra,
            )
    db.commit()

    veiculos_km = [
        {
            "uso_id": v.uso_id,
            "km_percorrido": v.km_percorrido,
            "km_referencia": v.km_referencia,
            "valor_km_extra": v.valor_km_extra,
        }
        for v in request.veiculos
    ]

    try:
        pdf_buffer = PDFNFService.generate_nf_empresa_pdf(db, request.empresa_id, veiculos_km)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar NF empresa: {}".format(str(e)))

    cnpj_clean = (empresa.cnpj or "").replace(".", "").replace("/", "").replace("-", "")
    mes_ano = datetime.now().strftime("%m_%Y")
    filename = "nf_consolidada_{}_{}.pdf".format(cnpj_clean, mes_ano)

    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


# ============================================================
# EXPORTAÇÕES UNIFICADAS (/exportar/)
# ============================================================
@router.get("/exportar/clientes")
def exportar_clientes(
    formato: str = "xlsx",
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export clients to CSV or XLSX."""
    if formato not in ("csv", "xlsx"):
        formato = "xlsx"

    parsed_start, parsed_end = _parse_optional_export_dates(data_inicio, data_fim)

    try:
        buffer = ExportacaoService.export_clientes(db, formato, parsed_start, parsed_end)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar clientes: {}".format(str(e)))

    data_str = datetime.now().strftime("%Y%m%d")
    filename = "clientes_{}.{}".format(data_str, formato)
    media = "text/csv; charset=utf-8" if formato == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media,
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.get("/exportar/veiculos")
def exportar_veiculos(
    formato: str = "xlsx",
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export vehicles to CSV or XLSX."""
    if formato not in ("csv", "xlsx"):
        formato = "xlsx"

    try:
        buffer = ExportacaoService.export_veiculos(db, formato, status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar veiculos: {}".format(str(e)))

    data_str = datetime.now().strftime("%Y%m%d")
    filename = "veiculos_{}.{}".format(data_str, formato)
    media = "text/csv; charset=utf-8" if formato == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media,
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.get("/exportar/contratos")
def exportar_contratos(
    formato: str = "xlsx",
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export contracts to CSV or XLSX."""
    if formato not in ("csv", "xlsx"):
        formato = "xlsx"

    parsed_start, parsed_end = _parse_optional_export_dates(data_inicio, data_fim)

    try:
        buffer = ExportacaoService.export_contratos(db, formato, parsed_start, parsed_end, status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar contratos: {}".format(str(e)))

    di = data_inicio or "geral"
    df = data_fim or datetime.now().strftime("%Y-%m-%d")
    filename = "contratos_{}_{}.{}".format(di, df, formato)
    media = "text/csv; charset=utf-8" if formato == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media,
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.get("/exportar/financeiro")
def exportar_financeiro(
    formato: str = "xlsx",
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export financial data to CSV or XLSX (multi-tab for XLSX)."""
    if formato not in ("csv", "xlsx"):
        formato = "xlsx"

    parsed_start, parsed_end = _parse_optional_export_dates(data_inicio, data_fim)

    try:
        buffer = ExportacaoService.export_financeiro(db, formato, parsed_start, parsed_end)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar financeiro: {}".format(str(e)))

    di = data_inicio or "geral"
    df = data_fim or datetime.now().strftime("%Y-%m-%d")
    filename = "financeiro_{}_{}.{}".format(di, df, formato)
    media = "text/csv; charset=utf-8" if formato == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media,
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


# ============================================================
# RELATÓRIO IPVA (mantido - funcionalidade única)
# ============================================================
@router.get("/ipva/pdf")
def get_relatorio_ipva_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate IPVA report PDF."""
    pdf_buffer = PDFService.generate_relatorio_ipva_pdf(db)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_ipva.pdf"},
    )
