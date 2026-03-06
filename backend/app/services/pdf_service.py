from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from app.models import (
    Contrato, Cliente, Veiculo, DespesaContrato, Quilometragem,
    CheckinCheckout, Empresa, DespesaVeiculo, DespesaLoja,
    DespesaOperacional, Seguro, IpvaRegistro, Multa, Manutencao,
    Reserva, Configuracao,
)


# === Shared Styles ===
DARK = colors.HexColor("#1f2937")
LIGHT_BG = colors.HexColor("#f1f5f9")
HEADER_BG = colors.HexColor("#1e40af")
PRIMARY = colors.HexColor("#2563eb")
SUCCESS = colors.HexColor("#059669")
DANGER = colors.HexColor("#dc2626")
WARNING = colors.HexColor("#d97706")
GRAY_BG = colors.HexColor("#e5e7eb")
WHITE = colors.white


def _get_empresa_info(db: Session) -> dict:
    """Get company info from configurations."""
    configs = db.query(Configuracao).all()
    info = {}
    for c in configs:
        info[c.chave] = c.valor
    return info


def _add_header(story, styles, title, subtitle=None, empresa_info=None):
    """Add standardized header to PDF."""
    empresa_nome = empresa_info.get("empresa_nome", "MPCARS") if empresa_info else "MPCARS"
    empresa_cnpj = empresa_info.get("empresa_cnpj", "") if empresa_info else ""

    header_style = ParagraphStyle("Header", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#6b7280"), alignment=TA_CENTER)
    title_style = ParagraphStyle("CustomTitle", parent=styles["Heading1"], fontSize=22, textColor=DARK, spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold")
    sub_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#4b5563"), alignment=TA_CENTER)

    story.append(Paragraph("<b>{}</b>".format(empresa_nome), ParagraphStyle("EmpName", parent=styles["Normal"], fontSize=14, textColor=PRIMARY, alignment=TA_CENTER, fontName="Helvetica-Bold")))
    if empresa_cnpj:
        story.append(Paragraph("CNPJ: {}".format(empresa_cnpj), header_style))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=12))
    story.append(Paragraph(title, title_style))
    if subtitle:
        story.append(Paragraph(subtitle, sub_style))
    story.append(Spacer(1, 16))


def _add_footer(story, styles):
    """Add standardized footer."""
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#d1d5db"), spaceAfter=8))
    footer_text = "Documento gerado automaticamente em {} | MPCARS Sistema de Gestao".format(datetime.now().strftime("%d/%m/%Y as %H:%M:%S"))
    story.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#9ca3af"), alignment=TA_CENTER)))


def _styled_table(data, col_widths=None, has_header=True):
    """Create a professionally styled table."""
    table = Table(data, colWidths=col_widths)
    style_commands = [
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
    ]
    if has_header:
        style_commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
        ])
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc")))
    table.setStyle(TableStyle(style_commands))
    return table


def _info_table(data):
    """Create a key-value info table."""
    table = Table(data, colWidths=[2.2 * inch, 4.3 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


class PDFService:
    """Service for generating PDF reports."""

    @staticmethod
    def generate_contrato_pdf(db: Session, contrato_id: int) -> BytesIO:
        """Generate professional contract PDF."""
        contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
        if not contrato:
            raise ValueError("Contrato nao encontrado")

        cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()
        veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
        empresa = None
        if cliente and cliente.empresa_id:
            empresa = db.query(Empresa).filter(Empresa.id == cliente.empresa_id).first()

        despesas = db.query(DespesaContrato).filter(DespesaContrato.contrato_id == contrato_id).all()
        empresa_info = _get_empresa_info(db)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*cm, bottomMargin=1*cm)
        story = []
        styles = getSampleStyleSheet()

        _add_header(story, styles, "CONTRATO DE ALUGUEL DE VEICULO", "Contrato N. {}".format(contrato.numero), empresa_info)

        # Contract info
        sec_style = ParagraphStyle("SecTitle", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY, spaceAfter=8)
        story.append(Paragraph("<b>DADOS DO CONTRATO</b>", sec_style))
        info_data = [
            ["Numero:", contrato.numero],
            ["Data de Criacao:", contrato.data_criacao.strftime("%d/%m/%Y") if contrato.data_criacao else "N/A"],
            ["Status:", contrato.status.upper()],
            ["Valor Diaria:", "R$ {:,.2f}".format(float(contrato.valor_diaria))],
            ["Valor Total:", "R$ {:,.2f}".format(float(contrato.valor_total)) if contrato.valor_total else "N/A"],
        ]
        story.append(_info_table(info_data))
        story.append(Spacer(1, 16))

        # PJ section if applicable
        if empresa:
            story.append(Paragraph("<b>DADOS DA EMPRESA (PESSOA JURIDICA)</b>", sec_style))
            pj_data = [
                ["Razao Social:", empresa.razao_social or empresa.nome],
                ["CNPJ:", empresa.cnpj],
                ["Endereco:", "{}, {}/{}".format(empresa.endereco or "", empresa.cidade or "", empresa.estado or "")],
                ["Telefone:", empresa.telefone or "N/A"],
                ["Email:", empresa.email or "N/A"],
                ["Contato:", empresa.contato_principal or "N/A"],
            ]
            story.append(_info_table(pj_data))
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>CONDUTOR AUTORIZADO</b>", sec_style))

        # Client info
        if not empresa:
            story.append(Paragraph("<b>DADOS DO CLIENTE (PESSOA FISICA)</b>", sec_style))
        client_data = [
            ["Nome:", cliente.nome if cliente else "N/A"],
            ["CPF:", cliente.cpf if cliente else "N/A"],
            ["RG:", (cliente.rg or "N/A") if cliente else "N/A"],
            ["Telefone:", (cliente.telefone or "N/A") if cliente else "N/A"],
            ["Email:", (cliente.email or "N/A") if cliente else "N/A"],
            ["CNH:", "{} - Cat. {}".format(cliente.numero_cnh or "N/A", cliente.categoria_cnh or "N/A") if cliente else "N/A"],
            ["Validade CNH:", cliente.validade_cnh.strftime("%d/%m/%Y") if cliente and cliente.validade_cnh else "N/A"],
            ["Endereco:", "{}, {}/{}".format(cliente.endereco_residencial or "", cliente.cidade_residencial or "", cliente.estado_residencial or "") if cliente else "N/A"],
        ]
        story.append(_info_table(client_data))
        story.append(Spacer(1, 16))

        # Vehicle info
        story.append(Paragraph("<b>DADOS DO VEICULO</b>", sec_style))
        vehicle_data = [
            ["Placa:", veiculo.placa if veiculo else "N/A"],
            ["Marca/Modelo:", "{} {}".format(veiculo.marca, veiculo.modelo) if veiculo else "N/A"],
            ["Ano:", str(veiculo.ano) if veiculo else "N/A"],
            ["Cor:", (veiculo.cor or "N/A") if veiculo else "N/A"],
            ["Combustivel:", (veiculo.combustivel or "N/A") if veiculo else "N/A"],
            ["Chassi:", (veiculo.chassis or "N/A") if veiculo else "N/A"],
            ["RENAVAM:", (veiculo.renavam or "N/A") if veiculo else "N/A"],
        ]
        story.append(_info_table(vehicle_data))
        story.append(Spacer(1, 16))

        # Rental period
        story.append(Paragraph("<b>PERIODO DE LOCACAO</b>", sec_style))
        period_data = [
            ["Data Inicio:", contrato.data_inicio.strftime("%d/%m/%Y %H:%M") if contrato.data_inicio else "N/A"],
            ["Data Fim:", contrato.data_fim.strftime("%d/%m/%Y %H:%M") if contrato.data_fim else "N/A"],
            ["KM Inicial:", "{:,.0f} km".format(contrato.km_inicial) if contrato.km_inicial else "N/A"],
            ["KM Final:", "{:,.0f} km".format(contrato.km_final) if contrato.km_final else "A definir"],
        ]
        story.append(_info_table(period_data))
        story.append(Spacer(1, 16))

        # Expenses
        if despesas:
            story.append(Paragraph("<b>DESPESAS ADICIONAIS</b>", sec_style))
            expense_rows = [["Tipo", "Descricao", "Valor"]]
            total_despesas = 0
            for d in despesas:
                val = float(d.valor) if d.valor else 0
                total_despesas += val
                expense_rows.append([d.tipo or "N/A", d.descricao or "N/A", "R$ {:,.2f}".format(val)])
            expense_rows.append(["", "TOTAL DESPESAS", "R$ {:,.2f}".format(total_despesas)])
            story.append(_styled_table(expense_rows, col_widths=[1.5*inch, 3*inch, 1.5*inch]))
            story.append(Spacer(1, 16))

        # Signatures
        story.append(Spacer(1, 40))
        sig_style = ParagraphStyle("Sig", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER)
        sig_data = [
            [Paragraph("____________________________", sig_style), Paragraph("____________________________", sig_style)],
            [Paragraph("LOCADOR", sig_style), Paragraph("LOCATARIO", sig_style)],
            [Paragraph(empresa_info.get("empresa_nome", "MPCARS"), sig_style), Paragraph(cliente.nome if cliente else "N/A", sig_style)],
        ]
        sig_table = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
        sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
        story.append(sig_table)

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_contratos_pdf(db: Session, data_inicio: str, data_fim: str) -> BytesIO:
        """Generate contracts report PDF."""
        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        empresa_info = _get_empresa_info(db)

        contratos = db.query(Contrato).filter(Contrato.data_criacao >= di, Contrato.data_criacao <= df).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()

        _add_header(story, styles, "RELATORIO DE CONTRATOS", "Periodo: {} a {}".format(di.strftime("%d/%m/%Y"), df.strftime("%d/%m/%Y")), empresa_info)

        total = len(contratos)
        ativos = sum(1 for c in contratos if c.status == "ativo")
        finalizados = sum(1 for c in contratos if c.status == "finalizado")
        valor_total = sum(float(c.valor_total or 0) for c in contratos)

        summary = [
            ["Total de Contratos", "Ativos", "Finalizados", "Valor Total"],
            [str(total), str(ativos), str(finalizados), "R$ {:,.2f}".format(valor_total)],
        ]
        story.append(_styled_table(summary, col_widths=[3.5*cm, 3.5*cm, 3.5*cm, 5*cm]))
        story.append(Spacer(1, 20))

        if contratos:
            rows = [["Numero", "Cliente", "Veiculo", "Inicio", "Fim", "Valor", "Status"]]
            for c in contratos:
                cliente = db.query(Cliente).filter(Cliente.id == c.cliente_id).first()
                veiculo = db.query(Veiculo).filter(Veiculo.id == c.veiculo_id).first()
                nome = cliente.nome if cliente else "N/A"
                if len(nome) > 20:
                    nome = nome[:18] + ".."
                rows.append([
                    c.numero, nome,
                    veiculo.placa if veiculo else "N/A",
                    c.data_inicio.strftime("%d/%m/%y") if c.data_inicio else "",
                    c.data_fim.strftime("%d/%m/%y") if c.data_fim else "",
                    "R$ {:,.2f}".format(float(c.valor_total or 0)),
                    c.status,
                ])
            story.append(_styled_table(rows, col_widths=[2.3*cm, 3.5*cm, 2*cm, 2*cm, 2*cm, 2.8*cm, 2*cm]))
        else:
            story.append(Paragraph("Nenhum contrato encontrado no periodo.", styles["Normal"]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_financeiro_pdf(db: Session, data_inicio: str, data_fim: str) -> BytesIO:
        """Generate financial report PDF with real data."""
        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        empresa_info = _get_empresa_info(db)

        contratos = db.query(Contrato).filter(Contrato.data_criacao >= di, Contrato.data_criacao <= df).all()
        receita_total = sum(float(c.valor_total or 0) for c in contratos)

        desp_contrato = db.query(DespesaContrato).filter(DespesaContrato.data_registro >= di, DespesaContrato.data_registro <= df).all()
        desp_veiculo = db.query(DespesaVeiculo).filter(DespesaVeiculo.data >= di, DespesaVeiculo.data <= df).all()
        desp_loja = db.query(DespesaLoja).all()

        total_desp_contrato = sum(float(d.valor or 0) for d in desp_contrato)
        total_desp_veiculo = sum(float(d.valor or 0) for d in desp_veiculo)
        total_desp_loja = sum(float(d.valor or 0) for d in desp_loja)
        despesa_total = total_desp_contrato + total_desp_veiculo + total_desp_loja
        lucro = receita_total - despesa_total

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        story = []
        styles = getSampleStyleSheet()

        _add_header(story, styles, "RELATORIO FINANCEIRO", "Periodo: {} a {}".format(di.strftime("%d/%m/%Y"), df.strftime("%d/%m/%Y")), empresa_info)

        summary_data = [
            ["Metrica", "Valor"],
            ["Total de Receitas (Contratos)", "R$ {:,.2f}".format(receita_total)],
            ["Despesas de Contratos", "R$ {:,.2f}".format(total_desp_contrato)],
            ["Despesas de Veiculos", "R$ {:,.2f}".format(total_desp_veiculo)],
            ["Despesas de Loja", "R$ {:,.2f}".format(total_desp_loja)],
            ["Total de Despesas", "R$ {:,.2f}".format(despesa_total)],
            ["Lucro Liquido", "R$ {:,.2f}".format(lucro)],
        ]
        story.append(_styled_table(summary_data, col_widths=[4*inch, 3*inch]))
        story.append(Spacer(1, 20))

        if contratos:
            sec_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY, spaceAfter=8)
            story.append(Paragraph("<b>DETALHAMENTO DE RECEITAS</b>", sec_style))
            rev_rows = [["Contrato", "Cliente", "Valor", "Status"]]
            for c in contratos:
                cliente = db.query(Cliente).filter(Cliente.id == c.cliente_id).first()
                rev_rows.append([c.numero, cliente.nome if cliente else "N/A", "R$ {:,.2f}".format(float(c.valor_total or 0)), c.status])
            story.append(_styled_table(rev_rows, col_widths=[3*cm, 5*cm, 4*cm, 3*cm]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_despesas_pdf(db: Session, data_inicio: str, data_fim: str) -> BytesIO:
        """Generate expenses report PDF."""
        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        empresa_info = _get_empresa_info(db)

        desp_contrato = db.query(DespesaContrato).filter(DespesaContrato.data_registro >= di, DespesaContrato.data_registro <= df).all()
        desp_veiculo = db.query(DespesaVeiculo).filter(DespesaVeiculo.data >= di, DespesaVeiculo.data <= df).all()
        desp_loja = db.query(DespesaLoja).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        story = []
        styles = getSampleStyleSheet()
        sec_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY, spaceAfter=8)

        _add_header(story, styles, "RELATORIO DE DESPESAS", "Periodo: {} a {}".format(di.strftime("%d/%m/%Y"), df.strftime("%d/%m/%Y")), empresa_info)

        story.append(Paragraph("<b>DESPESAS DE CONTRATOS</b>", sec_style))
        if desp_contrato:
            rows = [["Contrato", "Tipo", "Descricao", "Valor"]]
            for d in desp_contrato:
                rows.append([str(d.contrato_id), d.tipo or "", d.descricao or "", "R$ {:,.2f}".format(float(d.valor or 0))])
            rows.append(["", "", "TOTAL", "R$ {:,.2f}".format(sum(float(d.valor or 0) for d in desp_contrato))])
            story.append(_styled_table(rows, col_widths=[2.5*cm, 3*cm, 6*cm, 3.5*cm]))
        else:
            story.append(Paragraph("Nenhuma despesa de contrato no periodo.", styles["Normal"]))
        story.append(Spacer(1, 16))

        story.append(Paragraph("<b>DESPESAS DE VEICULOS</b>", sec_style))
        if desp_veiculo:
            rows = [["Veiculo", "Descricao", "KM", "Valor"]]
            for d in desp_veiculo:
                veiculo = db.query(Veiculo).filter(Veiculo.id == d.veiculo_id).first()
                rows.append([veiculo.placa if veiculo else str(d.veiculo_id), d.descricao or "", "{:,.0f}".format(d.km) if d.km else "", "R$ {:,.2f}".format(float(d.valor or 0))])
            rows.append(["", "", "TOTAL", "R$ {:,.2f}".format(sum(float(d.valor or 0) for d in desp_veiculo))])
            story.append(_styled_table(rows, col_widths=[3*cm, 6*cm, 2.5*cm, 3.5*cm]))
        else:
            story.append(Paragraph("Nenhuma despesa de veiculo no periodo.", styles["Normal"]))
        story.append(Spacer(1, 16))

        story.append(Paragraph("<b>DESPESAS DE LOJA</b>", sec_style))
        if desp_loja:
            rows = [["Mes/Ano", "Descricao", "Valor"]]
            for d in desp_loja:
                rows.append(["{:02d}/{}".format(d.mes, d.ano), d.descricao or "", "R$ {:,.2f}".format(float(d.valor or 0))])
            rows.append(["", "TOTAL", "R$ {:,.2f}".format(sum(float(d.valor or 0) for d in desp_loja))])
            story.append(_styled_table(rows, col_widths=[3*cm, 7.5*cm, 4.5*cm]))
        else:
            story.append(Paragraph("Nenhuma despesa de loja.", styles["Normal"]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_frota_pdf(db: Session) -> BytesIO:
        """Generate fleet report PDF."""
        empresa_info = _get_empresa_info(db)
        veiculos = db.query(Veiculo).filter(Veiculo.ativo == True).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()
        sec_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=13, textColor=WARNING, spaceAfter=8)

        _add_header(story, styles, "RELATORIO DE FROTA", "Data: {}".format(datetime.now().strftime("%d/%m/%Y")), empresa_info)

        total = len(veiculos)
        disponiveis = sum(1 for v in veiculos if v.status == "disponivel")
        alugados = sum(1 for v in veiculos if v.status == "alugado")
        manut = sum(1 for v in veiculos if v.status == "manutencao")
        valor_total = sum(float(v.valor_aquisicao or 0) for v in veiculos)

        summary = [
            ["Total Frota", "Disponiveis", "Alugados", "Manutencao", "Valor Total"],
            [str(total), str(disponiveis), str(alugados), str(manut), "R$ {:,.2f}".format(valor_total)],
        ]
        story.append(_styled_table(summary))
        story.append(Spacer(1, 20))

        if veiculos:
            rows = [["Placa", "Marca/Modelo", "Ano", "Cor", "KM Atual", "Status", "Aquisicao"]]
            for v in veiculos:
                rows.append([
                    v.placa, "{} {}".format(v.marca, v.modelo), str(v.ano), v.cor or "",
                    "{:,.0f}".format(v.km_atual) if v.km_atual else "0",
                    v.status, "R$ {:,.2f}".format(float(v.valor_aquisicao or 0)),
                ])
            story.append(_styled_table(rows, col_widths=[2*cm, 3.5*cm, 1.5*cm, 1.8*cm, 2*cm, 2.2*cm, 3*cm]))

        manutencoes = db.query(Manutencao).filter(Manutencao.status.in_(["agendada", "em_andamento"])).all()
        if manutencoes:
            story.append(Spacer(1, 20))
            story.append(Paragraph("<b>MANUTENCOES PENDENTES</b>", sec_style))
            m_rows = [["Veiculo", "Tipo", "Descricao", "Custo", "Status"]]
            for m in manutencoes:
                veiculo = db.query(Veiculo).filter(Veiculo.id == m.veiculo_id).first()
                m_rows.append([veiculo.placa if veiculo else "", m.tipo or "", (m.descricao or "")[:30], "R$ {:,.2f}".format(float(m.custo or 0)), m.status or ""])
            story.append(_styled_table(m_rows))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_clientes_pdf(db: Session) -> BytesIO:
        """Generate clients report PDF."""
        empresa_info = _get_empresa_info(db)
        clientes = db.query(Cliente).filter(Cliente.ativo == True).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()
        sec_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=13, textColor=PRIMARY, spaceAfter=8)

        _add_header(story, styles, "RELATORIO DE CLIENTES", "Data: {}".format(datetime.now().strftime("%d/%m/%Y")), empresa_info)

        total = len(clientes)
        com_empresa = sum(1 for c in clientes if c.empresa_id)
        sem_empresa = total - com_empresa

        summary = [
            ["Total Clientes", "Pessoa Fisica", "Vinculados a Empresa"],
            [str(total), str(sem_empresa), str(com_empresa)],
        ]
        story.append(_styled_table(summary))
        story.append(Spacer(1, 20))

        if clientes:
            rows = [["Nome", "CPF", "Telefone", "Cidade/UF", "Score", "Tipo"]]
            for c in clientes:
                tipo = "PF"
                if c.empresa_id:
                    empresa = db.query(Empresa).filter(Empresa.id == c.empresa_id).first()
                    tipo = empresa.nome[:15] if empresa else "PJ"
                rows.append([
                    c.nome[:20], c.cpf, c.telefone or "",
                    "{}/{}".format(c.cidade_residencial or "", c.estado_residencial or ""),
                    str(c.score or 0), tipo,
                ])
            story.append(_styled_table(rows, col_widths=[3.5*cm, 3*cm, 2.5*cm, 2.5*cm, 1.5*cm, 3*cm]))

        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>HISTORICO DE CONTRATOS POR CLIENTE</b>", sec_style))
        hist_rows = [["Cliente", "Contratos", "Valor Total", "Ultimo Status"]]
        for c in clientes:
            contracts = db.query(Contrato).filter(Contrato.cliente_id == c.id).all()
            if contracts:
                total_val = sum(float(ct.valor_total or 0) for ct in contracts)
                last = contracts[-1]
                hist_rows.append([c.nome[:20], str(len(contracts)), "R$ {:,.2f}".format(total_val), last.status])
        if len(hist_rows) > 1:
            story.append(_styled_table(hist_rows))
        else:
            story.append(Paragraph("Nenhum historico de contratos.", styles["Normal"]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_ipva_pdf(db: Session) -> BytesIO:
        """Generate IPVA report PDF."""
        empresa_info = _get_empresa_info(db)
        registros = db.query(IpvaRegistro).all()

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()

        _add_header(story, styles, "RELATORIO DE IPVA", "Data: {}".format(datetime.now().strftime("%d/%m/%Y")), empresa_info)

        total_ipva = sum(float(r.valor_ipva or 0) for r in registros)
        total_pago = sum(float(r.valor_pago or 0) for r in registros)
        pendente = total_ipva - total_pago
        pagos = sum(1 for r in registros if r.status == "pago")
        pendentes = sum(1 for r in registros if r.status in ("pendente", "parcial"))

        summary = [
            ["Total IPVA", "Total Pago", "Pendente", "Pagos", "Pendentes"],
            ["R$ {:,.2f}".format(total_ipva), "R$ {:,.2f}".format(total_pago), "R$ {:,.2f}".format(pendente), str(pagos), str(pendentes)],
        ]
        story.append(_styled_table(summary))
        story.append(Spacer(1, 20))

        if registros:
            rows = [["Veiculo", "Ano Ref.", "Valor Venal", "Aliquota", "Valor IPVA", "Pago", "Vencimento", "Status"]]
            for r in registros:
                veiculo = db.query(Veiculo).filter(Veiculo.id == r.veiculo_id).first()
                rows.append([
                    veiculo.placa if veiculo else str(r.veiculo_id),
                    str(r.ano_referencia),
                    "R$ {:,.2f}".format(float(r.valor_venal or 0)),
                    "{}%".format(r.aliquota),
                    "R$ {:,.2f}".format(float(r.valor_ipva or 0)),
                    "R$ {:,.2f}".format(float(r.valor_pago or 0)),
                    r.data_vencimento.strftime("%d/%m/%Y") if r.data_vencimento else "",
                    r.status,
                ])
            story.append(_styled_table(rows, col_widths=[2*cm, 1.5*cm, 2.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2*cm, 1.5*cm]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_nf_pdf(db: Session, relatorio_id: int) -> BytesIO:
        """Generate NF PDF."""
        from app.models import RelatorioNF as RelNF
        relatorio = db.query(RelNF).filter(RelNF.id == relatorio_id).first()
        empresa_info = _get_empresa_info(db)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        story = []
        styles = getSampleStyleSheet()

        _add_header(story, styles, "RELATORIO DE USO - NOTA FISCAL", "Relatorio N. {}".format(relatorio_id), empresa_info)

        if relatorio:
            veiculo = db.query(Veiculo).filter(Veiculo.id == relatorio.veiculo_id).first()
            empresa = db.query(Empresa).filter(Empresa.id == relatorio.empresa_id).first()

            info_data = [
                ["Veiculo:", "{} {} ({})".format(veiculo.marca, veiculo.modelo, veiculo.placa) if veiculo else "N/A"],
                ["Empresa:", empresa.nome if empresa else "N/A"],
                ["Periodo:", "{} a {}".format(relatorio.periodo_inicio.strftime("%d/%m/%Y") if relatorio.periodo_inicio else "", relatorio.periodo_fim.strftime("%d/%m/%Y") if relatorio.periodo_fim else "")],
                ["KM Percorrida:", "{:,.0f} km".format(relatorio.km_percorrida) if relatorio.km_percorrida else "0 km"],
                ["KM Excedente:", "{:,.0f} km".format(relatorio.km_excedente) if relatorio.km_excedente else "0 km"],
                ["Valor Total Extra:", "R$ {:,.2f}".format(float(relatorio.valor_total_extra or 0))],
            ]
            story.append(_info_table(info_data))
        else:
            story.append(Paragraph("Relatorio NF nao encontrado.", styles["Normal"]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer
