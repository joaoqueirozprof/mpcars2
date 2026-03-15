"""
PDF Generation Service for MPCARS NF (Nota Fiscal de Uso de Veículo por Empresa)
Gera relatório para enviar ao contador da empresa com cálculo de KM excedente.

Fluxo:
1. Recebe uso_id + km_percorrido (digitado pelo usuário)
2. Consulta km_referencia (KM permitido) e valor_km_extra (taxa por KM extra)
3. Se km_percorrido > km_referencia → calcula km_excedente e valor_extra
4. Inclui despesas associadas (DespesaNF)
5. Gera PDF profissional com todos os dados
"""

from datetime import datetime, date
from io import BytesIO
from decimal import Decimal
from typing import List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models import UsoVeiculoEmpresa, Empresa, Veiculo, DespesaNF, RelatorioNF


class PDFNFService:
    """Service for generating Nota Fiscal de Uso de Veículo PDFs"""

    HEADER_COLOR = HexColor("#3B5998")
    ALT_ROW_COLOR = HexColor("#F5F5F5")
    TOTAL_BG_COLOR = HexColor("#E8F4F8")
    BORDER_COLOR = HexColor("#CCCCCC")
    SUCCESS_COLOR = HexColor("#27AE60")
    DANGER_COLOR = HexColor("#E74C3C")

    @staticmethod
    def _format_currency(value) -> str:
        try:
            v = float(value or 0)
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "R$ 0,00"

    @staticmethod
    def _format_date(d) -> str:
        if not d:
            return "N/A"
        if isinstance(d, (datetime, date)):
            return d.strftime("%d/%m/%Y")
        return str(d)

    @staticmethod
    def _create_styles():
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            'title_nf', parent=styles['Title'],
            fontSize=18, spaceAfter=6, alignment=TA_CENTER,
            textColor=PDFNFService.HEADER_COLOR,
        ))
        styles.add(ParagraphStyle(
            'subtitle_nf', parent=styles['Normal'],
            fontSize=10, alignment=TA_CENTER, textColor=HexColor("#666666"),
        ))
        styles.add(ParagraphStyle(
            'section_header', parent=styles['Heading2'],
            fontSize=13, spaceAfter=6, spaceBefore=12,
            textColor=PDFNFService.HEADER_COLOR,
        ))
        styles.add(ParagraphStyle(
            'normal_nf', parent=styles['Normal'],
            fontSize=10, spaceAfter=3,
        ))
        styles.add(ParagraphStyle(
            'bold_nf', parent=styles['Normal'],
            fontSize=10, spaceAfter=3, fontName='Helvetica-Bold',
        ))
        styles.add(ParagraphStyle(
            'right_nf', parent=styles['Normal'],
            fontSize=10, alignment=TA_RIGHT,
        ))
        styles.add(ParagraphStyle(
            'center_nf', parent=styles['Normal'],
            fontSize=10, alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            'footer_nf', parent=styles['Normal'],
            fontSize=8, alignment=TA_CENTER, textColor=HexColor("#999999"),
        ))
        return styles

    @staticmethod
    def generate_nf_pdf(db, uso_id: int, km_percorrido: float = None,
                        km_referencia_override: float = None,
                        valor_km_extra_override: float = None) -> BytesIO:
        """
        Generate NF PDF for a single vehicle usage.

        Args:
            db: SQLAlchemy session
            uso_id: ID of UsoVeiculoEmpresa
            km_percorrido: KM digitado pelo usuário (se None, usa o que está no registro)
            km_referencia_override: KM permitido customizado (se None, usa do cadastro)
            valor_km_extra_override: Valor KM extra customizado (se None, usa do cadastro)
        """
        uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
        if not uso:
            raise ValueError(f"Uso de veiculo {uso_id} nao encontrado")

        empresa = db.query(Empresa).filter(Empresa.id == uso.empresa_id).first()
        if not empresa:
            raise ValueError(f"Empresa nao encontrada para uso {uso_id}")

        veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
        if not veiculo:
            raise ValueError(f"Veiculo nao encontrado para uso {uso_id}")

        despesas = db.query(DespesaNF).filter(DespesaNF.uso_id == uso_id).all()

        # Use km_percorrido from parameter, or from record
        if km_percorrido is not None:
            km_real = km_percorrido
        elif uso.km_percorrido:
            km_real = uso.km_percorrido
        else:
            km_real = 0

        # Use overrides or DB values
        km_permitido = km_referencia_override if km_referencia_override is not None else (uso.km_referencia or 0)
        taxa_km_extra = valor_km_extra_override if valor_km_extra_override is not None else float(uso.valor_km_extra or 0)

        # Calculate KM excedente
        km_excedente = max(0, km_real - km_permitido)
        valor_km_excedente = km_excedente * taxa_km_extra

        # Calculate despesas total
        total_despesas = sum(float(d.valor or 0) for d in despesas)

        # Valor base do faturamento corporativo: mensal / por periodo, nao diario.
        valor_diaria = float(uso.valor_diaria_empresa or 0)
        dias = 0
        if uso.data_inicio and uso.data_fim:
            delta = uso.data_fim - uso.data_inicio
            dias = max(1, delta.days)
        elif uso.data_inicio:
            delta = datetime.now() - uso.data_inicio
            dias = max(1, delta.days)
        total_diarias = valor_diaria

        total_geral = total_diarias + valor_km_excedente + total_despesas

        # Build PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
        )

        styles = PDFNFService._create_styles()
        story = []

        # === HEADER ===
        story.append(Paragraph("MPCARS - VEÍCULOS E LOCAÇÕES", styles['title_nf']))
        story.append(Paragraph("CNPJ: 52.471.526/0001-53 | Tel: (84) 99911-0504", styles['subtitle_nf']))
        story.append(Paragraph(
            "Rua Manoel Alexandre 1048 - LJ 02 - Princesinha do Oeste - CEP 59900-000 - Pau dos Ferros-RN",
            styles['subtitle_nf']
        ))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("<b>RELATÓRIO DE USO DE VEÍCULO - EMPRESA</b>", ParagraphStyle(
            'nf_main_title', parent=styles['Normal'],
            fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold',
            textColor=white, backColor=PDFNFService.HEADER_COLOR,
            spaceBefore=6, spaceAfter=6, leftIndent=-10, rightIndent=-10,
        )))
        story.append(Spacer(1, 0.3 * cm))

        # === SEÇÃO 1: DADOS DA EMPRESA ===
        story.append(Paragraph("1. DADOS DA EMPRESA LOCATÁRIA", styles['section_header']))
        empresa_data = [
            [Paragraph("<b>Razão Social:</b>", styles['normal_nf']),
             Paragraph(empresa.razao_social or empresa.nome or "N/A", styles['normal_nf'])],
            [Paragraph("<b>CNPJ:</b>", styles['normal_nf']),
             Paragraph(empresa.cnpj or "N/A", styles['normal_nf'])],
            [Paragraph("<b>Endereço:</b>", styles['normal_nf']),
             Paragraph(f"{empresa.endereco or ''}, {empresa.cidade or ''}-{empresa.estado or ''}", styles['normal_nf'])],
            [Paragraph("<b>Contato:</b>", styles['normal_nf']),
             Paragraph(f"{empresa.contato_principal or 'N/A'} | {empresa.telefone or ''} | {empresa.email or ''}", styles['normal_nf'])],
        ]
        t = Table(empresa_data, colWidths=[4 * cm, 13 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), PDFNFService.ALT_ROW_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

        # === SEÇÃO 2: DADOS DO VEÍCULO ===
        story.append(Paragraph("2. DADOS DO VEÍCULO", styles['section_header']))
        veiculo_data = [
            [Paragraph("<b>Placa:</b>", styles['normal_nf']),
             Paragraph(veiculo.placa or "N/A", styles['normal_nf']),
             Paragraph("<b>Marca/Modelo:</b>", styles['normal_nf']),
             Paragraph(f"{veiculo.marca or ''} {veiculo.modelo or ''}", styles['normal_nf'])],
            [Paragraph("<b>Ano:</b>", styles['normal_nf']),
             Paragraph(str(veiculo.ano or "N/A"), styles['normal_nf']),
             Paragraph("<b>Cor:</b>", styles['normal_nf']),
             Paragraph(veiculo.cor or "N/A", styles['normal_nf'])],
        ]
        t = Table(veiculo_data, colWidths=[4 * cm, 4.5 * cm, 4 * cm, 4.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), PDFNFService.ALT_ROW_COLOR),
            ("BACKGROUND", (2, 0), (2, -1), PDFNFService.ALT_ROW_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

        # === SEÇÃO 3: PERÍODO E QUILOMETRAGEM ===
        story.append(Paragraph("3. PERÍODO E QUILOMETRAGEM", styles['section_header']))

        # Status da KM
        if km_excedente > 0:
            km_status = f'<font color="#E74C3C"><b>EXCEDEU {km_excedente:.1f} KM</b></font>'
        else:
            km_status = f'<font color="#27AE60"><b>DENTRO DO LIMITE</b></font>'

        # Get NF number if exists
        relatorio = db.query(RelatorioNF).filter(RelatorioNF.uso_id == uso_id).order_by(RelatorioNF.id.desc()).first()
        nf_numero = relatorio.id if relatorio else "N/A"

        km_data = [
            [Paragraph("<b>Período Utilizado/Faturado:</b>", styles['normal_nf']),
             Paragraph(f"{PDFNFService._format_date(uso.data_inicio)} até {PDFNFService._format_date(uso.data_fim)} – NF {nf_numero} – Valor {PDFNFService._format_currency(total_geral)}", styles['normal_nf']),
             Paragraph("", styles['normal_nf']),
             Paragraph("", styles['normal_nf'])],
            [Paragraph("<b>KM Percorrido:</b>", styles['bold_nf']),
             Paragraph(f"<b>{km_real:,.1f} km</b>", styles['normal_nf']),
             Paragraph("<b>KM Permitido:</b>", styles['normal_nf']),
             Paragraph(f"{km_permitido:,.1f} km", styles['normal_nf'])],
            [Paragraph("<b>KM Excedente:</b>", styles['bold_nf']),
             Paragraph(f"<b>{km_excedente:,.1f} km</b>", styles['normal_nf']),
             Paragraph("<b>Status:</b>", styles['normal_nf']),
             Paragraph(km_status, styles['normal_nf'])],
            [Paragraph("<b>Taxa por KM Extra:</b>", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(taxa_km_extra), styles['normal_nf']),
             Paragraph("<b>Valor KM Excedente:</b>", styles['bold_nf']),
             Paragraph(f"<b>{PDFNFService._format_currency(valor_km_excedente)}</b>", styles['normal_nf'])],
        ]
        t = Table(km_data, colWidths=[4 * cm, 4.5 * cm, 4 * cm, 4.5 * cm])
        style_cmds = [
            ("BACKGROUND", (0, 0), (0, -1), PDFNFService.ALT_ROW_COLOR),
            ("BACKGROUND", (2, 0), (2, -1), PDFNFService.ALT_ROW_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if km_excedente > 0:
            style_cmds.append(("BACKGROUND", (1, 3), (1, 3), HexColor("#FFEBEE")))
        t.setStyle(TableStyle(style_cmds))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

        # === SEÇÃO 4: DESPESAS ===
        if despesas:
            story.append(Paragraph("4. DESPESAS DO VEÍCULO", styles['section_header']))
            desp_header = [
                Paragraph("<b>Tipo</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white)),
                Paragraph("<b>Descrição</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white)),
                Paragraph("<b>Data</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white)),
                Paragraph("<b>Valor</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            ]
            desp_data = [desp_header]
            for d in despesas:
                desp_data.append([
                    Paragraph(getattr(d, 'tipo', None) or "Geral", styles['normal_nf']),
                    Paragraph(d.descricao or "N/A", styles['normal_nf']),
                    Paragraph(PDFNFService._format_date(d.data), styles['normal_nf']),
                    Paragraph(PDFNFService._format_currency(d.valor), styles['right_nf']),
                ])
            desp_data.append([
                Paragraph("<b>TOTAL DESPESAS</b>", styles['bold_nf']),
                Paragraph("", styles['normal_nf']),
                Paragraph("", styles['normal_nf']),
                Paragraph(f"<b>{PDFNFService._format_currency(total_despesas)}</b>", styles['right_nf']),
            ])

            t = Table(desp_data, colWidths=[3.5 * cm, 6.5 * cm, 3 * cm, 4 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), PDFNFService.HEADER_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [white, PDFNFService.ALT_ROW_COLOR]),
                ("BACKGROUND", (0, -1), (-1, -1), PDFNFService.TOTAL_BG_COLOR),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.3 * cm))

        # === SEÇÃO 5: RESUMO FINANCEIRO ===
        section_num = 5 if despesas else 4
        story.append(Paragraph(f"{section_num}. RESUMO FINANCEIRO", styles['section_header']))

        resumo_data = [
            [Paragraph("<b>Valor Base</b>", styles['normal_nf']),
             Paragraph(f"Período faturado a {PDFNFService._format_currency(valor_diaria)}", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(total_diarias), styles['right_nf'])],
            [Paragraph("<b>KM Excedente</b>", styles['normal_nf']),
             Paragraph(f"{km_excedente:,.1f} km x {PDFNFService._format_currency(taxa_km_extra)}/km", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(valor_km_excedente), styles['right_nf'])],
            [Paragraph("<b>Despesas</b>", styles['normal_nf']),
             Paragraph(f"{len(despesas)} item(s)", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(total_despesas), styles['right_nf'])],
            [Paragraph("<b>TOTAL GERAL A PAGAR</b>", ParagraphStyle('tg', parent=styles['bold_nf'], fontSize=12)),
             Paragraph("", styles['normal_nf']),
             Paragraph(f"<b>{PDFNFService._format_currency(total_geral)}</b>",
                        ParagraphStyle('tgv', parent=styles['right_nf'], fontSize=12, fontName='Helvetica-Bold'))],
        ]
        t = Table(resumo_data, colWidths=[4 * cm, 8.5 * cm, 4.5 * cm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("BACKGROUND", (0, -1), (-1, -1), PDFNFService.HEADER_COLOR),
            ("TEXTCOLOR", (0, -1), (-1, -1), white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))

        # === FOOTER ===
        story.append(Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | MPCARS Sistema de Locação",
            styles['footer_nf']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_nf_empresa_pdf(
        db,
        empresa_id: int,
        veiculos_km: List[dict],
    ) -> BytesIO:
        """
        Generate a consolidated NF PDF for multiple vehicles of a company.

        Args:
            db: SQLAlchemy session
            empresa_id: ID of the company
            veiculos_km: List of dicts with {uso_id: int, km_percorrido: float}
        """
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            raise ValueError("Empresa nao encontrada")

        styles = PDFNFService._create_styles()

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
        )

        story = []

        # === HEADER ===
        story.append(Paragraph("MPCARS - VEÍCULOS E LOCAÇÕES", styles['title_nf']))
        story.append(Paragraph("CNPJ: 52.471.526/0001-53 | Tel: (84) 99911-0504", styles['subtitle_nf']))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph("<b>RELATÓRIO CONSOLIDADO DE USO DE VEÍCULOS - EMPRESA</b>", ParagraphStyle(
            'nf_main_title2', parent=styles['Normal'],
            fontSize=13, alignment=TA_CENTER, fontName='Helvetica-Bold',
            textColor=white, backColor=PDFNFService.HEADER_COLOR,
            spaceBefore=4, spaceAfter=6, leftIndent=-10, rightIndent=-10,
        )))
        story.append(Spacer(1, 0.2 * cm))

        # === DADOS DA EMPRESA ===
        story.append(Paragraph("EMPRESA LOCATÁRIA", styles['section_header']))
        empresa_info = [
            [Paragraph("<b>Razão Social:</b>", styles['normal_nf']),
             Paragraph(empresa.razao_social or empresa.nome or "N/A", styles['normal_nf']),
             Paragraph("<b>CNPJ:</b>", styles['normal_nf']),
             Paragraph(empresa.cnpj or "N/A", styles['normal_nf'])],
            [Paragraph("<b>Contato:</b>", styles['normal_nf']),
             Paragraph(empresa.contato_principal or "N/A", styles['normal_nf']),
             Paragraph("<b>Telefone:</b>", styles['normal_nf']),
             Paragraph(empresa.telefone or "N/A", styles['normal_nf'])],
        ]
        t = Table(empresa_info, colWidths=[3.5 * cm, 5 * cm, 3.5 * cm, 5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), PDFNFService.ALT_ROW_COLOR),
            ("BACKGROUND", (2, 0), (2, -1), PDFNFService.ALT_ROW_COLOR),
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

        # === TABELA RESUMO DE TODOS OS VEÍCULOS ===
        story.append(Paragraph("RESUMO POR VEÍCULO", styles['section_header']))

        header_row = [
            Paragraph("<b>Placa</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white)),
            Paragraph("<b>Modelo</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white)),
            Paragraph("<b>KM Percorrido</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            Paragraph("<b>KM Permitido</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            Paragraph("<b>KM Excedente</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            Paragraph("<b>Valor Extra</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            Paragraph("<b>Despesas</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
            Paragraph("<b>Total</b>", ParagraphStyle('h', parent=styles['normal_nf'], textColor=white, alignment=TA_RIGHT)),
        ]
        table_data = [header_row]

        total_geral = 0
        total_km_percorrido = 0
        total_km_excedente = 0
        total_valor_extra = 0
        total_despesas_geral = 0
        total_diarias_geral = 0

        for item in veiculos_km:
            uso_id = item.get("uso_id")
            km_input = item.get("km_percorrido", 0)
            km_ref_override = item.get("km_referencia")
            taxa_override = item.get("valor_km_extra")

            uso = db.query(UsoVeiculoEmpresa).filter(UsoVeiculoEmpresa.id == uso_id).first()
            if not uso:
                continue

            veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
            despesas = db.query(DespesaNF).filter(DespesaNF.uso_id == uso_id).all()

            km_real = km_input or uso.km_percorrido or 0
            km_permitido = km_ref_override if km_ref_override is not None else (uso.km_referencia or 0)
            taxa = taxa_override if taxa_override is not None else float(uso.valor_km_extra or 0)
            km_exc = max(0, km_real - km_permitido)
            valor_exc = km_exc * taxa
            total_desp = sum(float(d.valor or 0) for d in despesas)

            # Valor base do faturamento corporativo: fixo por ciclo medido.
            valor_diaria = float(uso.valor_diaria_empresa or 0)
            dias = 0
            if uso.data_inicio and uso.data_fim:
                dias = max(1, (uso.data_fim - uso.data_inicio).days)
            elif uso.data_inicio:
                dias = max(1, (datetime.now() - uso.data_inicio).days)
            total_diarias = valor_diaria

            subtotal = total_diarias + valor_exc + total_desp

            total_geral += subtotal
            total_km_percorrido += km_real
            total_km_excedente += km_exc
            total_valor_extra += valor_exc
            total_despesas_geral += total_desp
            total_diarias_geral += total_diarias

            # Color for excedente
            km_exc_text = f"{km_exc:,.1f}" if km_exc > 0 else "0"
            if km_exc > 0:
                km_exc_para = Paragraph(f'<font color="#E74C3C"><b>{km_exc_text}</b></font>', styles['right_nf'])
            else:
                km_exc_para = Paragraph(f'<font color="#27AE60">{km_exc_text}</font>', styles['right_nf'])

            table_data.append([
                Paragraph(veiculo.placa if veiculo else "N/A", styles['normal_nf']),
                Paragraph(f"{veiculo.marca or ''} {veiculo.modelo or ''}" if veiculo else "N/A", styles['normal_nf']),
                Paragraph(f"{km_real:,.1f}", styles['right_nf']),
                Paragraph(f"{km_permitido:,.1f}", styles['right_nf']),
                km_exc_para,
                Paragraph(PDFNFService._format_currency(valor_exc), styles['right_nf']),
                Paragraph(PDFNFService._format_currency(total_desp), styles['right_nf']),
                Paragraph(f"<b>{PDFNFService._format_currency(subtotal)}</b>", styles['right_nf']),
            ])

        # Total row
        table_data.append([
            Paragraph("<b>TOTAL</b>", styles['bold_nf']),
            Paragraph("", styles['normal_nf']),
            Paragraph(f"<b>{total_km_percorrido:,.1f}</b>", styles['right_nf']),
            Paragraph("", styles['right_nf']),
            Paragraph(f"<b>{total_km_excedente:,.1f}</b>", styles['right_nf']),
            Paragraph(f"<b>{PDFNFService._format_currency(total_valor_extra)}</b>", styles['right_nf']),
            Paragraph(f"<b>{PDFNFService._format_currency(total_despesas_geral)}</b>", styles['right_nf']),
            Paragraph(f"<b>{PDFNFService._format_currency(total_geral)}</b>", styles['right_nf']),
        ])

        col_widths = [2 * cm, 3 * cm, 2 * cm, 2 * cm, 2 * cm, 2.2 * cm, 2 * cm, 2.3 * cm]
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PDFNFService.HEADER_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [white, PDFNFService.ALT_ROW_COLOR]),
            ("BACKGROUND", (0, -1), (-1, -1), PDFNFService.TOTAL_BG_COLOR),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

        # === TOTAL GERAL ===
        story.append(Paragraph("TOTAL GERAL", styles['section_header']))
        totais_data = [
            [Paragraph("<b>Total Base</b>", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(total_diarias_geral), styles['right_nf'])],
            [Paragraph("<b>Total KM Excedente</b>", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(total_valor_extra), styles['right_nf'])],
            [Paragraph("<b>Total Despesas</b>", styles['normal_nf']),
             Paragraph(PDFNFService._format_currency(total_despesas_geral), styles['right_nf'])],
            [Paragraph("<b>TOTAL GERAL A PAGAR</b>", ParagraphStyle('tg2', parent=styles['bold_nf'], fontSize=12)),
             Paragraph(f"<b>{PDFNFService._format_currency(total_geral)}</b>",
                        ParagraphStyle('tgv2', parent=styles['right_nf'], fontSize=12, fontName='Helvetica-Bold'))],
        ]
        t = Table(totais_data, colWidths=[12 * cm, 5 * cm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, PDFNFService.BORDER_COLOR),
            ("BACKGROUND", (0, -1), (-1, -1), PDFNFService.HEADER_COLOR),
            ("TEXTCOLOR", (0, -1), (-1, -1), white),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))

        # === FOOTER ===
        story.append(Paragraph(
            f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | MPCARS Sistema de Locação",
            styles['footer_nf']
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
