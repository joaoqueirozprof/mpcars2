"""
Financial Report PDF Generation Service
Generates comprehensive financial reports using ReportLab with data from database.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from io import BytesIO
from typing import Optional, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from app.models import (
    Contrato, Cliente, Veiculo, DespesaVeiculo, DespesaLoja,
    Seguro, ParcelaSeguro, IpvaRegistro, IpvaParcela, Multa, Configuracao
)


class PDFFinanceiroService:
    """Service for generating financial reports in PDF format."""

    # Modern color palette
    COLOR_PRIMARY = colors.HexColor("#1E3A5F")
    COLOR_SECONDARY = colors.HexColor("#2980B9")
    COLOR_ACCENT = colors.HexColor("#3498DB")
    COLOR_POSITIVE = colors.HexColor("#27AE60")
    COLOR_NEGATIVE = colors.HexColor("#E74C3C")
    COLOR_WARNING = colors.HexColor("#F39C12")
    COLOR_HEADER_BG = colors.HexColor("#1E3A5F")
    COLOR_HEADER_TEXT = colors.white
    COLOR_ROW_ALT = colors.HexColor("#FFFFFF")
    COLOR_ROW_ALT_2 = colors.HexColor("#F0F4F8")
    COLOR_BORDER = colors.HexColor("#D5DDE5")
    COLOR_LIGHT_BG = colors.HexColor("#EBF5FB")
    COLOR_CARD_BG = colors.HexColor("#F8FAFB")

    # Chart colors for categories
    CHART_COLORS = [
        colors.HexColor("#3498DB"),  # Veiculos - blue
        colors.HexColor("#E67E22"),  # Loja - orange
        colors.HexColor("#9B59B6"),  # Seguros - purple
        colors.HexColor("#1ABC9C"),  # Licenciamento - teal
        colors.HexColor("#E74C3C"),  # Multas - red
    ]

    PAGE_WIDTH = A4[0]
    CONTENT_WIDTH = A4[0] - 1.6 * cm

    @staticmethod
    def _format_currency(value) -> str:
        """Format value as Brazilian currency."""
        if value is None:
            return "R$ 0,00"
        try:
            value = Decimal(str(value))
            formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {formatted}"
        except (ValueError, TypeError):
            return "R$ 0,00"

    @staticmethod
    def _format_date(date_obj) -> str:
        """Format date as DD/MM/YYYY."""
        if date_obj is None:
            return "-"
        try:
            if isinstance(date_obj, str):
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
            return date_obj.strftime("%d/%m/%Y")
        except (ValueError, AttributeError):
            return "-"

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d")

    @staticmethod
    def _get_date_range(data_inicio: str, data_fim: str) -> Tuple[datetime, datetime]:
        data_inicio_dt = PDFFinanceiroService._parse_date(data_inicio)
        data_fim_dt = PDFFinanceiroService._parse_date(data_fim)
        data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
        return data_inicio_dt, data_fim_dt

    @staticmethod
    def _create_styles() -> Dict:
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=PDFFinanceiroService.COLOR_PRIMARY,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        section_style = ParagraphStyle(
            'CustomSection',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.white,
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            backColor=PDFFinanceiroService.COLOR_PRIMARY,
            borderPadding=(8, 10, 8, 10),
            leading=18,
        )

        subsection_style = ParagraphStyle(
            'CustomSubsection',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=PDFFinanceiroService.COLOR_PRIMARY,
            spaceAfter=4,
            spaceBefore=8,
            fontName='Helvetica-Bold',
            borderPadding=(4, 6, 4, 6),
            backColor=PDFFinanceiroService.COLOR_LIGHT_BG,
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            leading=12,
        )

        normal_left = ParagraphStyle(
            'CustomNormalLeft',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            leading=12,
        )

        normal_right = ParagraphStyle(
            'CustomNormalRight',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_RIGHT,
            leading=12,
        )

        header_cell = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            leading=11,
        )

        return {
            'title': title_style,
            'section': section_style,
            'subsection': subsection_style,
            'normal': normal_style,
            'normal_left': normal_left,
            'normal_right': normal_right,
            'header_cell': header_cell,
        }

    # =========================================================================
    # DATA FETCHING
    # =========================================================================

    @staticmethod
    def _get_resumo_consolidado(db, data_inicio: str, data_fim: str) -> Dict:
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)

        # Revenue
        receita_total = db.query(Contrato).filter(
            Contrato.status == 'finalizado',
            Contrato.data_fim >= data_inicio_dt,
            Contrato.data_fim <= data_fim_dt
        ).with_entities(Contrato.valor_total).all()
        receita_total = sum([r[0] or Decimal('0') for r in receita_total])

        # Vehicle expenses
        despesa_veiculo = db.query(DespesaVeiculo).filter(
            DespesaVeiculo.data >= data_inicio_dt,
            DespesaVeiculo.data <= data_fim_dt
        ).with_entities(DespesaVeiculo.valor).all()
        total_desp_veiculo = sum([d[0] or Decimal('0') for d in despesa_veiculo])

        # Shop expenses
        despesa_loja = db.query(DespesaLoja).all()
        total_desp_loja = Decimal('0')
        data_inicio_date = PDFFinanceiroService._parse_date(data_inicio).date()
        data_fim_date = PDFFinanceiroService._parse_date(data_fim).date()
        for despesa in despesa_loja:
            if hasattr(despesa, 'mes') and hasattr(despesa, 'ano') and despesa.mes and despesa.ano:
                despesa_date = date(despesa.ano, despesa.mes, 1)
                if data_inicio_date <= despesa_date <= data_fim_date:
                    total_desp_loja += despesa.valor or Decimal('0')

        # Insurance - parcelas with vencimento in period
        parcela_seguro = db.query(ParcelaSeguro).filter(
            ParcelaSeguro.vencimento >= data_inicio_dt,
            ParcelaSeguro.vencimento <= data_fim_dt,
        ).with_entities(ParcelaSeguro.valor).all()
        total_seguros = sum([p[0] or Decimal('0') for p in parcela_seguro])

        # Licenciamento - parcelas with vencimento in period
        parcela_lic = db.query(IpvaParcela).filter(
            IpvaParcela.vencimento >= data_inicio_dt,
            IpvaParcela.vencimento <= data_fim_dt,
        ).with_entities(IpvaParcela.valor).all()
        total_licenciamento = sum([p[0] or Decimal('0') for p in parcela_lic])

        # Fines
        multas = db.query(Multa).filter(
            Multa.data_pagamento >= data_inicio_dt,
            Multa.data_pagamento <= data_fim_dt
        ).with_entities(Multa.valor).all()
        total_multas = sum([m[0] or Decimal('0') for m in multas])

        despesa_total = total_desp_veiculo + total_desp_loja + total_seguros + total_licenciamento + total_multas
        lucro = receita_total - despesa_total
        margem = (lucro / receita_total * 100) if receita_total > 0 else Decimal('0')

        return {
            'receita_total': receita_total,
            'despesa_total': despesa_total,
            'lucro': lucro,
            'margem': margem,
            'desp_veiculos': total_desp_veiculo,
            'desp_loja': total_desp_loja,
            'desp_seguros': total_seguros,
            'desp_licenciamento': total_licenciamento,
            'desp_multas': total_multas,
            'num_contratos': len(receita_total) if isinstance(receita_total, list) else 0,
        }

    @staticmethod
    def _get_receitas_detalhadas(db, data_inicio: str, data_fim: str) -> List:
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)
        contratos = db.query(Contrato).filter(
            Contrato.status == 'finalizado',
            Contrato.data_fim >= data_inicio_dt,
            Contrato.data_fim <= data_fim_dt
        ).all()

        dados = []
        for contrato in contratos:
            cliente_nome = contrato.cliente.nome if contrato.cliente else "-"
            veiculo_info = "-"
            if contrato.veiculo:
                veiculo_info = f"{contrato.veiculo.placa} - {contrato.veiculo.marca} {contrato.veiculo.modelo}"

            if contrato.qtd_diarias:
                qtd_diarias = contrato.qtd_diarias
            elif contrato.data_inicio and contrato.data_fim:
                qtd_diarias = (contrato.data_fim.date() - contrato.data_inicio.date()).days
            else:
                qtd_diarias = 0

            dados.append({
                'id': str(contrato.id),
                'cliente': cliente_nome,
                'veiculo': veiculo_info,
                'data_inicio': PDFFinanceiroService._format_date(contrato.data_inicio),
                'data_fim': PDFFinanceiroService._format_date(contrato.data_fim),
                'qtd_diarias': str(qtd_diarias),
                'valor_total': contrato.valor_total or Decimal('0')
            })
        return dados

    @staticmethod
    def _get_despesas_veiculo(db, data_inicio: str, data_fim: str) -> List:
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)
        despesas = db.query(DespesaVeiculo).filter(
            DespesaVeiculo.data >= data_inicio_dt,
            DespesaVeiculo.data <= data_fim_dt
        ).all()

        dados = []
        for despesa in despesas:
            veiculo_info = "-"
            if despesa.veiculo:
                placa = despesa.veiculo.placa or ""
                modelo = despesa.veiculo.modelo or ""
                marca = despesa.veiculo.marca or ""
                veiculo_info = f"{placa} - {marca} {modelo}".strip(" -")
                if not veiculo_info or veiculo_info == "-":
                    veiculo_info = f"Veículo #{despesa.veiculo_id}"

            dados.append({
                'veiculo': veiculo_info,
                'tipo': despesa.tipo or "-",
                'descricao': despesa.descricao or "-",
                'data': PDFFinanceiroService._format_date(despesa.data),
                'valor': despesa.valor or Decimal('0')
            })
        return dados

    @staticmethod
    def _get_despesas_loja(db, data_inicio: str, data_fim: str) -> List:
        data_inicio_date = PDFFinanceiroService._parse_date(data_inicio).date()
        data_fim_date = PDFFinanceiroService._parse_date(data_fim).date()
        despesas = db.query(DespesaLoja).all()

        dados = []
        for despesa in despesas:
            if hasattr(despesa, 'mes') and hasattr(despesa, 'ano') and despesa.mes and despesa.ano:
                despesa_date = date(despesa.ano, despesa.mes, 1)
                if data_inicio_date <= despesa_date <= data_fim_date:
                    dados.append({
                        'categoria': despesa.categoria or "-",
                        'descricao': despesa.descricao or "-",
                        'mes_ano': f"{despesa.mes:02d}/{despesa.ano}",
                        'valor': despesa.valor or Decimal('0')
                    })
        return dados

    @staticmethod
    def _get_despesas_seguros(db, data_inicio: str, data_fim: str) -> List:
        """Get insurance installments whose vencimento falls within the period."""
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)
        from sqlalchemy.orm import joinedload
        parcelas = db.query(ParcelaSeguro).options(
            joinedload(ParcelaSeguro.seguro).joinedload(Seguro.veiculo)
        ).filter(
            ParcelaSeguro.vencimento >= data_inicio_dt,
            ParcelaSeguro.vencimento <= data_fim_dt,
        ).all()

        dados = []
        for parcela in parcelas:
            apolice = "-"
            seguradora = "-"
            veiculo_info = "-"
            if parcela.seguro:
                apolice = parcela.seguro.numero_apolice or "-"
                seguradora = parcela.seguro.seguradora or "-"
                if parcela.seguro.veiculo:
                    placa = parcela.seguro.veiculo.placa or ""
                    marca = parcela.seguro.veiculo.marca or ""
                    modelo = parcela.seguro.veiculo.modelo or ""
                    veiculo_info = f"{placa} - {marca} {modelo}".strip(" -")

            status_label = "Pago" if parcela.status == "pago" else "Pendente"

            dados.append({
                'seguradora': seguradora,
                'apolice': apolice,
                'veiculo': veiculo_info,
                'parcela': f"{parcela.numero_parcela}",
                'vencimento': PDFFinanceiroService._format_date(parcela.vencimento),
                'status': status_label,
                'valor': parcela.valor or Decimal('0')
            })
        return dados

    @staticmethod
    def _get_despesas_licenciamento(db, data_inicio: str, data_fim: str) -> List:
        """Get licensing installments whose vencimento falls within the period."""
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)
        from sqlalchemy.orm import joinedload
        parcelas = db.query(IpvaParcela).options(
            joinedload(IpvaParcela.ipva).joinedload(IpvaRegistro.veiculo)
        ).filter(
            IpvaParcela.vencimento >= data_inicio_dt,
            IpvaParcela.vencimento <= data_fim_dt,
        ).all()

        dados = []
        for parcela in parcelas:
            veiculo_info = "-"
            ano_ref = "-"
            if parcela.ipva:
                ano_ref = str(parcela.ipva.ano_referencia or "-")
                if parcela.ipva.veiculo:
                    placa = parcela.ipva.veiculo.placa or ""
                    marca = parcela.ipva.veiculo.marca or ""
                    modelo = parcela.ipva.veiculo.modelo or ""
                    veiculo_info = f"{placa} - {marca} {modelo}".strip(" -")

            status_label = "Pago" if parcela.status == "pago" else "Pendente"

            dados.append({
                'veiculo': veiculo_info,
                'ano_ref': ano_ref,
                'parcela': f"{parcela.numero_parcela}",
                'vencimento': PDFFinanceiroService._format_date(parcela.vencimento),
                'status': status_label,
                'valor': parcela.valor or Decimal('0')
            })
        return dados

    @staticmethod
    def _get_despesas_multas(db, data_inicio: str, data_fim: str) -> List:
        data_inicio_dt, data_fim_dt = PDFFinanceiroService._get_date_range(data_inicio, data_fim)
        multas = db.query(Multa).filter(
            Multa.data_pagamento >= data_inicio_dt,
            Multa.data_pagamento <= data_fim_dt
        ).all()

        dados = []
        for multa in multas:
            veiculo_info = "-"
            if multa.veiculo:
                veiculo_info = f"{multa.veiculo.placa} - {multa.veiculo.marca or ''} {multa.veiculo.modelo or ''}".strip()

            dados.append({
                'veiculo': veiculo_info,
                'descricao': multa.descricao or "-",
                'valor': multa.valor or Decimal('0'),
                'data_pagamento': PDFFinanceiroService._format_date(multa.data_pagamento)
            })
        return dados

    # =========================================================================
    # PDF BUILDING BLOCKS
    # =========================================================================

    @staticmethod
    def _build_table(headers: List[str], rows: List[List], col_widths=None, show_total=True, total_col=-1) -> Table:
        """Build a professionally styled table."""
        styles = PDFFinanceiroService._create_styles()

        table_data = [[Paragraph(f"<b>{h}</b>", styles['header_cell']) for h in headers]]

        total_valor = Decimal('0')
        for idx, row in enumerate(rows):
            styled_row = []
            for i, cell in enumerate(row):
                if i == len(row) - 1 and isinstance(cell, (Decimal, float, int)):
                    total_valor += Decimal(str(cell))
                    styled_row.append(Paragraph(
                        PDFFinanceiroService._format_currency(cell),
                        styles['normal_right']
                    ))
                elif isinstance(cell, (Decimal, float, int)):
                    styled_row.append(Paragraph(
                        PDFFinanceiroService._format_currency(cell),
                        styles['normal_right']
                    ))
                else:
                    styled_row.append(Paragraph(str(cell)[:50], styles['normal_left']))
            table_data.append(styled_row)

        if show_total and rows:
            total_row = [Paragraph("", styles['normal_left'])] * len(headers)
            total_row[0] = Paragraph("<b>TOTAL</b>", styles['normal_left'])
            total_row[-1] = Paragraph(
                f"<b>{PDFFinanceiroService._format_currency(total_valor)}</b>",
                styles['normal_right']
            )
            table_data.append(total_row)

        if not col_widths:
            col_widths = [None] * len(headers)

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style_commands = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), PDFFinanceiroService.COLOR_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            # Borders
            ('LINEBELOW', (0, 0), (-1, 0), 1, PDFFinanceiroService.COLOR_PRIMARY),
            ('LINEBELOW', (0, -1), (-1, -1), 1, PDFFinanceiroService.COLOR_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2 if show_total and rows else -1),
             [PDFFinanceiroService.COLOR_ROW_ALT, PDFFinanceiroService.COLOR_ROW_ALT_2]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Align last column right
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]

        if show_total and rows:
            style_commands.extend([
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, PDFFinanceiroService.COLOR_PRIMARY),
                ('BACKGROUND', (0, -1), (-1, -1), PDFFinanceiroService.COLOR_LIGHT_BG),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ])

        table.setStyle(TableStyle(style_commands))
        return table

    @staticmethod
    def _create_header(data_inicio: str, data_fim: str) -> List:
        styles = PDFFinanceiroService._create_styles()
        elements = []

        # Top line
        elements.append(HRFlowable(
            width="100%", thickness=3,
            color=PDFFinanceiroService.COLOR_PRIMARY,
            spaceAfter=10
        ))

        # Title
        titulo = Paragraph("RELATÓRIO FINANCEIRO", styles['title'])
        elements.append(titulo)

        # Subtitle with company name
        subtitulo = Paragraph(
            "<font color='#666666'>MPCARS — Sistema de Locação de Veículos</font>",
            ParagraphStyle('sub', parent=styles['normal'], fontSize=10, spaceAfter=8)
        )
        elements.append(subtitulo)

        elements.append(HRFlowable(
            width="100%", thickness=1,
            color=PDFFinanceiroService.COLOR_BORDER,
            spaceAfter=10
        ))

        # Period and generation info
        data_inicio_fmt = PDFFinanceiroService._format_date(data_inicio)
        data_fim_fmt = PDFFinanceiroService._format_date(data_fim)
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        info_data = [
            [
                Paragraph(f"<b>Período:</b> {data_inicio_fmt} a {data_fim_fmt}", styles['normal_left']),
                Paragraph(f"<b>Gerado em:</b> {agora}", styles['normal_right']),
            ]
        ]
        info_table = Table(info_data, colWidths=[PDFFinanceiroService.CONTENT_WIDTH / 2] * 2)
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3 * cm))

        return elements

    @staticmethod
    def _create_resumo_consolidado(resumo: Dict) -> List:
        styles = PDFFinanceiroService._create_styles()
        elements = []

        elements.append(Paragraph("RESUMO CONSOLIDADO", styles['section']))
        elements.append(Spacer(1, 0.3 * cm))

        receita = resumo['receita_total']
        despesa = resumo['despesa_total']
        lucro = resumo['lucro']
        margem = resumo['margem']

        # Summary cards as a clean table
        lucro_color = "#27AE60" if lucro >= 0 else "#E74C3C"
        lucro_label = "LUCRO" if lucro >= 0 else "PREJUÍZO"

        card_data = [
            [
                Paragraph(f"<font size=7 color='#888888'><b>RECEITA TOTAL</b></font><br/>"
                         f"<font size=14 color='#2980B9'><b>{PDFFinanceiroService._format_currency(receita)}</b></font>",
                         styles['normal']),
                Paragraph(f"<font size=7 color='#888888'><b>DESPESA TOTAL</b></font><br/>"
                         f"<font size=14 color='#E67E22'><b>{PDFFinanceiroService._format_currency(despesa)}</b></font>",
                         styles['normal']),
                Paragraph(f"<font size=7 color='#888888'><b>{lucro_label}</b></font><br/>"
                         f"<font size=14 color='{lucro_color}'><b>{PDFFinanceiroService._format_currency(lucro)}</b></font>",
                         styles['normal']),
                Paragraph(f"<font size=7 color='#888888'><b>MARGEM</b></font><br/>"
                         f"<font size=14 color='#1E3A5F'><b>{margem:.1f}%</b></font>",
                         styles['normal']),
            ]
        ]

        w = PDFFinanceiroService.CONTENT_WIDTH / 4
        cards = Table(card_data, colWidths=[w, w, w, w])
        cards.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PDFFinanceiroService.COLOR_CARD_BG),
            ('BOX', (0, 0), (0, 0), 1, PDFFinanceiroService.COLOR_BORDER),
            ('BOX', (1, 0), (1, 0), 1, PDFFinanceiroService.COLOR_BORDER),
            ('BOX', (2, 0), (2, 0), 1, PDFFinanceiroService.COLOR_BORDER),
            ('BOX', (3, 0), (3, 0), 1, PDFFinanceiroService.COLOR_BORDER),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(cards)
        elements.append(Spacer(1, 0.4 * cm))

        # Breakdown mini table
        breakdown_data = [
            [Paragraph("<b>Categoria de Despesa</b>", styles['header_cell']),
             Paragraph("<b>Valor</b>", styles['header_cell']),
             Paragraph("<b>% do Total</b>", styles['header_cell'])],
        ]

        categorias = [
            ("Despesas com Veículos", resumo['desp_veiculos']),
            ("Despesas da Loja", resumo['desp_loja']),
            ("Seguros (parcelas)", resumo['desp_seguros']),
            ("Licenciamento (parcelas)", resumo['desp_licenciamento']),
            ("Multas", resumo['desp_multas']),
        ]

        desp_total = resumo['despesa_total']
        for cat_name, cat_val in categorias:
            pct = float(cat_val / desp_total * 100) if desp_total > 0 else 0
            breakdown_data.append([
                Paragraph(cat_name, styles['normal_left']),
                Paragraph(PDFFinanceiroService._format_currency(cat_val), styles['normal_right']),
                Paragraph(f"{pct:.1f}%", styles['normal_right']),
            ])

        breakdown_data.append([
            Paragraph("<b>TOTAL DESPESAS</b>", styles['normal_left']),
            Paragraph(f"<b>{PDFFinanceiroService._format_currency(desp_total)}</b>", styles['normal_right']),
            Paragraph("<b>100%</b>", styles['normal_right']),
        ])

        bw = PDFFinanceiroService.CONTENT_WIDTH
        bt = Table(breakdown_data, colWidths=[bw * 0.5, bw * 0.25, bw * 0.25])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PDFFinanceiroService.COLOR_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2),
             [PDFFinanceiroService.COLOR_ROW_ALT, PDFFinanceiroService.COLOR_ROW_ALT_2]),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, PDFFinanceiroService.COLOR_PRIMARY),
            ('BACKGROUND', (0, -1), (-1, -1), PDFFinanceiroService.COLOR_LIGHT_BG),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(bt)
        elements.append(Spacer(1, 0.5 * cm))

        return elements

    @staticmethod
    def _create_receitas_detalhadas(dados: List) -> List:
        styles = PDFFinanceiroService._create_styles()
        elements = []

        elements.append(Paragraph("RECEITAS — CONTRATOS FINALIZADOS", styles['section']))
        elements.append(Spacer(1, 0.2 * cm))

        if not dados:
            elements.append(Paragraph("<i>Nenhum contrato finalizado no período</i>", styles['normal']))
            elements.append(Spacer(1, 0.3 * cm))
            return elements

        headers = ["#", "Cliente", "Veículo", "Saída", "Devolução", "Dias", "Valor"]
        rows = []
        for item in dados:
            rows.append([
                item['id'],
                item['cliente'],
                item['veiculo'],
                item['data_inicio'],
                item['data_fim'],
                item['qtd_diarias'],
                item['valor_total'],
            ])

        cw = PDFFinanceiroService.CONTENT_WIDTH
        table = PDFFinanceiroService._build_table(
            headers, rows,
            col_widths=[cw*0.06, cw*0.18, cw*0.24, cw*0.12, cw*0.12, cw*0.08, cw*0.20]
        )
        elements.append(table)
        elements.append(Spacer(1, 0.4 * cm))
        return elements

    @staticmethod
    def _create_despesas_detalhadas(db, data_inicio: str, data_fim: str) -> List:
        styles = PDFFinanceiroService._create_styles()
        elements = []

        elements.append(Paragraph("DESPESAS DETALHADAS", styles['section']))
        elements.append(Spacer(1, 0.2 * cm))

        cw = PDFFinanceiroService.CONTENT_WIDTH

        # 1. Vehicle expenses
        elements.append(Paragraph("Despesas com Veículos", styles['subsection']))
        despesas_veiculo = PDFFinanceiroService._get_despesas_veiculo(db, data_inicio, data_fim)
        if despesas_veiculo:
            rows = [[d['veiculo'], d['tipo'], d['descricao'], d['data'], d['valor']] for d in despesas_veiculo]
            table = PDFFinanceiroService._build_table(
                ["Veículo", "Tipo", "Descrição", "Data", "Valor"], rows,
                col_widths=[cw*0.25, cw*0.15, cw*0.25, cw*0.15, cw*0.20]
            )
            elements.append(table)
        else:
            elements.append(Paragraph("<i>Nenhuma despesa de veículo no período</i>", styles['normal']))
        elements.append(Spacer(1, 0.3 * cm))

        # 2. Shop expenses
        elements.append(Paragraph("Despesas da Loja", styles['subsection']))
        despesas_loja = PDFFinanceiroService._get_despesas_loja(db, data_inicio, data_fim)
        if despesas_loja:
            rows = [[d['categoria'], d['descricao'], d['mes_ano'], d['valor']] for d in despesas_loja]
            table = PDFFinanceiroService._build_table(
                ["Categoria", "Descrição", "Mês/Ano", "Valor"], rows,
                col_widths=[cw*0.25, cw*0.35, cw*0.15, cw*0.25]
            )
            elements.append(table)
        else:
            elements.append(Paragraph("<i>Nenhuma despesa da loja no período</i>", styles['normal']))
        elements.append(Spacer(1, 0.3 * cm))

        # 3. Insurance parcelas
        elements.append(Paragraph("Seguros (Parcelas no Período)", styles['subsection']))
        despesas_seguros = PDFFinanceiroService._get_despesas_seguros(db, data_inicio, data_fim)
        if despesas_seguros:
            rows = [[d['seguradora'], d['apolice'], d['veiculo'], d['parcela'], d['vencimento'], d['status'], d['valor']]
                    for d in despesas_seguros]
            table = PDFFinanceiroService._build_table(
                ["Seguradora", "Apólice", "Veículo", "Parc.", "Vencimento", "Status", "Valor"], rows,
                col_widths=[cw*0.16, cw*0.14, cw*0.16, cw*0.07, cw*0.14, cw*0.12, cw*0.21]
            )
            elements.append(table)
        else:
            elements.append(Paragraph("<i>Nenhuma parcela de seguro no período</i>", styles['normal']))
        elements.append(Spacer(1, 0.3 * cm))

        # 4. Licenciamento parcelas
        elements.append(Paragraph("Licenciamento (Parcelas no Período)", styles['subsection']))
        despesas_lic = PDFFinanceiroService._get_despesas_licenciamento(db, data_inicio, data_fim)
        if despesas_lic:
            rows = [[d['veiculo'], d['ano_ref'], d['parcela'], d['vencimento'], d['status'], d['valor']]
                    for d in despesas_lic]
            table = PDFFinanceiroService._build_table(
                ["Veículo", "Ano Ref.", "Parc.", "Vencimento", "Status", "Valor"], rows,
                col_widths=[cw*0.25, cw*0.12, cw*0.08, cw*0.18, cw*0.14, cw*0.23]
            )
            elements.append(table)
        else:
            elements.append(Paragraph("<i>Nenhuma parcela de licenciamento no período</i>", styles['normal']))
        elements.append(Spacer(1, 0.3 * cm))

        # 5. Fines
        elements.append(Paragraph("Multas", styles['subsection']))
        despesas_multas = PDFFinanceiroService._get_despesas_multas(db, data_inicio, data_fim)
        if despesas_multas:
            rows = [[d['veiculo'], d['descricao'], d['data_pagamento'], d['valor']] for d in despesas_multas]
            table = PDFFinanceiroService._build_table(
                ["Veículo", "Descrição", "Data Pgto.", "Valor"], rows,
                col_widths=[cw*0.30, cw*0.30, cw*0.20, cw*0.20]
            )
            elements.append(table)
        else:
            elements.append(Paragraph("<i>Nenhuma multa paga no período</i>", styles['normal']))
        elements.append(Spacer(1, 0.3 * cm))

        return elements

    @staticmethod
    def _create_comparativo_visual(resumo: Dict) -> List:
        """Create a professional visual comparison of expenses using a pie chart."""
        styles = PDFFinanceiroService._create_styles()
        elements = []

        elements.append(Paragraph("COMPOSIÇÃO DE DESPESAS", styles['section']))
        elements.append(Spacer(1, 0.3 * cm))

        categorias = [
            ("Veículos", resumo['desp_veiculos']),
            ("Loja", resumo['desp_loja']),
            ("Seguros", resumo['desp_seguros']),
            ("Licenciamento", resumo['desp_licenciamento']),
            ("Multas", resumo['desp_multas']),
        ]

        total = sum([v for _, v in categorias])

        if total <= 0:
            elements.append(Paragraph("<i>Sem despesas no período para exibir gráfico</i>", styles['normal']))
            return elements

        # Filter out zero categories
        active_cats = [(name, val) for name, val in categorias if val > 0]

        # Create pie chart
        d = Drawing(400, 200)

        pie = Pie()
        pie.x = 30
        pie.y = 10
        pie.width = 160
        pie.height = 160
        pie.data = [float(v) for _, v in active_cats]
        pie.labels = None
        pie.slices.strokeWidth = 1
        pie.slices.strokeColor = colors.white

        for i, (name, val) in enumerate(active_cats):
            color_idx = categorias.index((name, val)) if (name, val) in categorias else i
            if color_idx < len(PDFFinanceiroService.CHART_COLORS):
                pie.slices[i].fillColor = PDFFinanceiroService.CHART_COLORS[color_idx]
            pie.slices[i].popout = 3

        d.add(pie)

        # Legend
        y_pos = 155
        for i, (name, val) in enumerate(active_cats):
            pct = float(val / total * 100)
            color_idx = categorias.index((name, val)) if (name, val) in categorias else i
            chart_color = PDFFinanceiroService.CHART_COLORS[color_idx] if color_idx < len(PDFFinanceiroService.CHART_COLORS) else colors.grey

            # Color box
            d.add(Rect(230, y_pos, 12, 12, fillColor=chart_color, strokeWidth=0))
            # Label
            d.add(String(248, y_pos + 2,
                        f"{name}: {PDFFinanceiroService._format_currency(val)} ({pct:.1f}%)",
                        fontName='Helvetica', fontSize=9, fillColor=colors.HexColor("#333333")))
            y_pos -= 22

        elements.append(d)
        elements.append(Spacer(1, 0.3 * cm))

        # Horizontal bar chart as table
        bar_data = [[
            Paragraph("<b>Categoria</b>", styles['header_cell']),
            Paragraph("<b>Valor</b>", styles['header_cell']),
            Paragraph("<b>Participação</b>", styles['header_cell']),
        ]]

        cw = PDFFinanceiroService.CONTENT_WIDTH
        bar_col_width = cw * 0.40

        for i, (name, val) in enumerate(categorias):
            pct = float(val / total * 100) if total > 0 else 0
            color_idx = i
            chart_color = PDFFinanceiroService.CHART_COLORS[color_idx] if color_idx < len(PDFFinanceiroService.CHART_COLORS) else colors.grey

            # Create mini bar
            bar_width = max(2, pct / 100 * float(bar_col_width - 50))
            bar_drawing = Drawing(float(bar_col_width), 16)
            bar_drawing.add(Rect(0, 3, bar_width, 10,
                               fillColor=chart_color, strokeWidth=0))
            bar_drawing.add(String(bar_width + 4, 4, f"{pct:.1f}%",
                                  fontName='Helvetica-Bold', fontSize=8,
                                  fillColor=colors.HexColor("#333333")))

            bar_data.append([
                Paragraph(f"<b>{name}</b>", styles['normal_left']),
                Paragraph(PDFFinanceiroService._format_currency(val), styles['normal_right']),
                bar_drawing,
            ])

        bt = Table(bar_data, colWidths=[cw * 0.25, cw * 0.20, cw * 0.55])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PDFFinanceiroService.COLOR_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [PDFFinanceiroService.COLOR_ROW_ALT, PDFFinanceiroService.COLOR_ROW_ALT_2]),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, PDFFinanceiroService.COLOR_PRIMARY),
        ]))
        elements.append(bt)
        elements.append(Spacer(1, 0.5 * cm))

        return elements

    @staticmethod
    def _add_footer(canvas, doc):
        """Add footer to each page."""
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor("#999999"))
        canvas.drawString(0.8 * cm, 0.6 * cm,
                         f"MPCARS — Relatório Financeiro — Página {doc.page}")
        canvas.drawRightString(A4[0] - 0.8 * cm, 0.6 * cm,
                              f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        # Top border line on every page
        canvas.setStrokeColor(PDFFinanceiroService.COLOR_PRIMARY)
        canvas.setLineWidth(2)
        canvas.line(0.8 * cm, A4[1] - 0.6 * cm, A4[0] - 0.8 * cm, A4[1] - 0.6 * cm)
        canvas.restoreState()

    # =========================================================================
    # MAIN GENERATOR
    # =========================================================================

    @staticmethod
    def generate_relatorio_financeiro_pdf(db, data_inicio: str, data_fim: str) -> BytesIO:
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.8 * cm,
            leftMargin=0.8 * cm,
            topMargin=1.2 * cm,
            bottomMargin=1.2 * cm
        )

        elements = []

        # Header
        elements.extend(PDFFinanceiroService._create_header(data_inicio, data_fim))

        # Consolidated Summary
        resumo = PDFFinanceiroService._get_resumo_consolidado(db, data_inicio, data_fim)
        elements.extend(PDFFinanceiroService._create_resumo_consolidado(resumo))

        # Page break
        elements.append(PageBreak())

        # Detailed Revenue
        receitas = PDFFinanceiroService._get_receitas_detalhadas(db, data_inicio, data_fim)
        elements.extend(PDFFinanceiroService._create_receitas_detalhadas(receitas))

        # Detailed Expenses
        elements.extend(PDFFinanceiroService._create_despesas_detalhadas(db, data_inicio, data_fim))

        # Page break before chart
        elements.append(PageBreak())

        # Visual Comparison
        elements.extend(PDFFinanceiroService._create_comparativo_visual(resumo))

        # Build PDF with footer
        doc.build(elements, onFirstPage=PDFFinanceiroService._add_footer,
                  onLaterPages=PDFFinanceiroService._add_footer)

        buffer.seek(0)
        return buffer
