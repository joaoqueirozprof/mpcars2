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
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.deps import get_current_user, require_page_access
from app.models.user import User
from app.models import Contrato, RelatorioNF, UsoVeiculoEmpresa, Empresa, Veiculo
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


# ============================================================
# PDF 1 - CONTRATO DE LOCAÇÃO
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
def get_nf_pdf(
    uso_id: int,
    km_percorrido: Optional[float] = None,
    km_referencia: Optional[float] = None,
    valor_km_extra: Optional[float] = None,
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

    if km_percorrido is not None:
        uso.km_percorrido = km_percorrido
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

    for item in request.veiculos:
        uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == item.uso_id).first()
        if uso:
            uso.km_percorrido = item.km_percorrido
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

    try:
        buffer = ExportacaoService.export_clientes(db, formato, data_inicio, data_fim)
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

    try:
        buffer = ExportacaoService.export_contratos(db, formato, data_inicio, data_fim, status_filter)
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

    try:
        buffer = ExportacaoService.export_financeiro(db, formato, data_inicio, data_fim)
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
