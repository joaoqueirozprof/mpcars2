from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models import Contrato, RelatorioNF, UsoVeiculoEmpresa, Empresa, Veiculo
from app.services.pdf_service import PDFService
from app.services.export_service import ExportService
from app.services.pdf_contrato import PDFContratoService
from app.services.pdf_financeiro import PDFFinanceiroService
from app.services.pdf_nf import PDFNFService
from app.services.exportacao import ExportacaoService


router = APIRouter(prefix="/relatorios", tags=["Relatorios"])


# ============================================================
# PDF 1 - CONTRATO DE LOCAÇÃO (spec route)
# ============================================================
@router.get("/contrato/{contrato_id}/pdf")
def get_contrato_pdf(
    contrato_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate contract PDF report (uses original layout matching physical form)."""
    contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
    if not contrato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato nao encontrado")

    if not contrato.cliente_id or not contrato.veiculo_id:
        raise HTTPException(status_code=422, detail="Contrato com dados incompletos (cliente ou veiculo ausente)")

    veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
    placa = veiculo.placa if veiculo else "000"
    data_str = datetime.now().strftime("%Y%m%d")

    try:
        pdf_buffer = PDFService.generate_contrato_pdf(db, contrato_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar PDF do contrato: {}".format(str(e)))

    filename = "contrato_{}_{}_{}".format(contrato_id, placa, data_str)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="{}.pdf"'.format(filename)},
    )


# ============================================================
# PDF 2 - RELATÓRIO FINANCEIRO (spec route)
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
def get_nf_pdf(
    uso_id: int,
    km_percorrido: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate NF PDF for a single vehicle usage.
    km_percorrido: KM digitado pelo usuario (se omitido, usa o do registro).
    """
    uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
    if not uso:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uso de veiculo nao encontrado")

    empresa = db.query(Empresa).filter(Empresa.id == uso.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa nao encontrada para este uso")

    # Save km_percorrido if provided
    if km_percorrido is not None:
        uso.km_percorrido = km_percorrido
        db.commit()

    try:
        pdf_buffer = PDFNFService.generate_nf_pdf(db, uso_id, km_percorrido)
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


# ============================================================
# PDF 3B - NF CONSOLIDADA (múltiplos veículos de uma empresa)
# ============================================================
from pydantic import BaseModel as PydanticBase
from typing import List as TypingList


class VeiculoKM(PydanticBase):
    uso_id: int
    km_percorrido: float


class NFEmpresaRequest(PydanticBase):
    empresa_id: int
    veiculos: TypingList[VeiculoKM]


@router.post("/nf/empresa/pdf")
def get_nf_empresa_pdf(
    request: NFEmpresaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate consolidated NF PDF for multiple vehicles of a company.
    Send empresa_id + list of {uso_id, km_percorrido} for each vehicle.
    """
    empresa = db.query(Empresa).filter(Empresa.id == request.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada")

    if not request.veiculos:
        raise HTTPException(status_code=400, detail="Nenhum veiculo informado")

    # Save km_percorrido for each vehicle
    for item in request.veiculos:
        uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == item.uso_id).first()
        if uso:
            uso.km_percorrido = item.km_percorrido
    db.commit()

    veiculos_km = [{"uso_id": v.uso_id, "km_percorrido": v.km_percorrido} for v in request.veiculos]

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
# EXPORTAÇÕES UNIFICADAS (spec routes: /exportar/)
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

    try:
        buffer = ExportacaoService.export_clientes(db, formato, data_inicio, data_fim)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar clientes: {}".format(str(e)))

    data_str = datetime.now().strftime("%Y%m%d")
    filename = "clientes_{}.{}".format(data_str, formato)

    if formato == "csv":
        media = "text/csv; charset=utf-8"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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

    if formato == "csv":
        media = "text/csv; charset=utf-8"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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

    try:
        buffer = ExportacaoService.export_contratos(db, formato, data_inicio, data_fim, status_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar contratos: {}".format(str(e)))

    di = data_inicio or "geral"
    df = data_fim or datetime.now().strftime("%Y-%m-%d")
    filename = "contratos_{}_{}.{}".format(di, df, formato)

    if formato == "csv":
        media = "text/csv; charset=utf-8"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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

    try:
        buffer = ExportacaoService.export_financeiro(db, formato, data_inicio, data_fim)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao exportar financeiro: {}".format(str(e)))

    di = data_inicio or "geral"
    df = data_fim or datetime.now().strftime("%Y-%m-%d")
    filename = "financeiro_{}_{}.{}".format(di, df, formato)

    if formato == "csv":
        media = "text/csv; charset=utf-8"
    else:
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type=media,
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


# ============================================================
# LEGACY ROUTES (kept for backward compatibility)
# ============================================================
@router.get("/contratos/pdf")
def get_relatorio_contratos_pdf(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate contracts report PDF (legacy)."""
    try:
        datetime.strptime(data_inicio, "%Y-%m-%d")
        datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de data invalido")

    pdf_buffer = PDFService.generate_relatorio_contratos_pdf(db, data_inicio, data_fim)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_contratos_{}_{}.pdf".format(data_inicio, data_fim)},
    )


@router.get("/receitas/pdf")
def get_relatorio_receitas_pdf(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate revenue report PDF (legacy)."""
    try:
        datetime.strptime(data_inicio, "%Y-%m-%d")
        datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de data invalido")

    pdf_buffer = PDFService.generate_relatorio_receitas_pdf(db, data_inicio, data_fim)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_receitas_{}_{}.pdf".format(data_inicio, data_fim)},
    )


@router.get("/despesas/pdf")
def get_relatorio_despesas_pdf(
    data_inicio: str,
    data_fim: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate expenses report PDF (legacy)."""
    try:
        datetime.strptime(data_inicio, "%Y-%m-%d")
        datetime.strptime(data_fim, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato de data invalido")

    pdf_buffer = PDFService.generate_relatorio_despesas_pdf(db, data_inicio, data_fim)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_despesas_{}_{}.pdf".format(data_inicio, data_fim)},
    )


@router.get("/frota/pdf")
def get_relatorio_frota_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate fleet report PDF (legacy)."""
    pdf_buffer = PDFService.generate_relatorio_frota_pdf(db)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_frota.pdf"},
    )


@router.get("/clientes/pdf")
def get_relatorio_clientes_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate clients report PDF (legacy)."""
    pdf_buffer = PDFService.generate_relatorio_clientes_pdf(db)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_clientes.pdf"},
    )


@router.get("/ipva/pdf")
def get_relatorio_ipva_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate IPVA report PDF (legacy)."""
    pdf_buffer = PDFService.generate_relatorio_ipva_pdf(db)
    return StreamingResponse(
        iter([pdf_buffer.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=relatorio_ipva.pdf"},
    )


# Legacy export routes (kept for backward compatibility)
@router.get("/contratos/xlsx")
def export_contratos_xlsx(
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export contracts to XLSX (legacy)."""
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    buffer = ExportService.export_contratos_xlsx(db, filters)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=contratos.xlsx"},
    )


@router.get("/contratos/csv")
def export_contratos_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export contracts to CSV (legacy)."""
    buffer = ExportService.export_contratos_csv(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contratos.csv"},
    )


@router.get("/veiculos/xlsx")
def export_veiculos_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export vehicles to XLSX (legacy)."""
    buffer = ExportService.export_veiculos_xlsx(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=veiculos.xlsx"},
    )


@router.get("/clientes/xlsx")
def export_clientes_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export clients to XLSX (legacy)."""
    buffer = ExportService.export_clientes_xlsx(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=clientes.xlsx"},
    )


@router.get("/despesas/xlsx")
def export_despesas_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export expenses to XLSX (legacy)."""
    buffer = ExportService.export_despesas_xlsx(db)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=despesas.xlsx"},
    )
