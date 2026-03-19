import os
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
    Reserva, Configuracao, UsoVeiculoEmpresa, RelatorioNF,
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
    def generate_contrato_pdf(db: Session, contrato_id: int, veiculo_id: int = None) -> BytesIO:
        """Generate contract PDF matching the MPCARS official template with vehicle inspection diagram.
        
        Args:
            db: Database session
            contrato_id: Contract ID
            veiculo_id: Optional vehicle ID to use for the PDF (useful for company contracts with multiple vehicles)
        """
        from reportlab.pdfgen import canvas as pdfcanvas

        contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
        if not contrato:
            raise ValueError("Contrato nao encontrado")

        cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()
        # Use the provided veiculo_id if different from contract's main vehicle
        target_veiculo_id = veiculo_id if veiculo_id else contrato.veiculo_id
        veiculo = db.query(Veiculo).filter(Veiculo.id == target_veiculo_id).first()
        empresa = None
        if cliente and cliente.empresa_id:
            empresa = db.query(Empresa).filter(Empresa.id == cliente.empresa_id).first()

        buffer = BytesIO()
        c = pdfcanvas.Canvas(buffer, pagesize=A4)
        w, h = A4  # 595.27 x 841.89

        # === PAGE 1: CONTRACT FORM ===
        margin = 28
        col_left_w = w / 2 - margin
        col_right_w = w / 2 - margin
        y_start = h - margin

        # --- HEADER ---
        # Logo text MPCARS
        c.setFillColor(colors.HexColor("#1a1a1a"))
        c.setFont("Helvetica-Bold", 28)
        c.drawString(margin, y_start - 10, "MPCARS")
        c.setFont("Helvetica", 8)
        c.drawString(margin, y_start - 22, "VEICULOS E LOCACOES")

        # Title right
        c.setFont("Helvetica-Bold", 18)
        c.drawRightString(w - margin, y_start - 6, "CONTRATO DE LOCACAO")

        # Company info
        c.setFont("Helvetica", 7)
        c.drawString(margin, y_start - 36, "CNPJ.: 52.471.526/0001-53       84 99911-0504")
        c.drawString(margin, y_start - 46, "RUA MANOEL ALEXANDRE 1048 - LJ 02 - EDIFICIO COMERCIAL E RESIDENCIAL")
        c.drawString(margin, y_start - 54, "PRINCESINHA DO OESTE - CEP 59900-000 - PAU DOS FERROS-RN")

        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        y_line = y_start - 60
        c.line(margin, y_line, w - margin, y_line)

        # Helper functions
        def draw_label_value(x, y, label, value, label_w=120, font_size=7):
            c.setFont("Helvetica-Bold", font_size)
            c.drawString(x, y, label)
            c.setFont("Helvetica", font_size)
            c.drawString(x + label_w, y, str(value or ""))

        def draw_section_title(y, title, sec_x=None, sec_w=None):
            """Draw section title box. sec_x/sec_w control position and width."""
            sx = sec_x if sec_x is not None else margin
            sw = sec_w if sec_w is not None else (w - 2 * margin)
            c.setFillColor(colors.HexColor("#1a1a1a"))
            c.setFont("Helvetica-Bold", 9)
            box_h = 16
            c.rect(sx, y - box_h, sw, box_h, fill=0)
            c.drawCentredString(sx + sw / 2, y - box_h + 4, title)
            return y - box_h - 4

        def draw_field_box(x, y, label, value, width, height=14):
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.5)
            c.rect(x, y - height, width, height)
            c.setFont("Helvetica-Bold", 5.5)
            c.setFillColor(colors.black)
            c.drawString(x + 2, y - 5, label)
            c.setFont("Helvetica", 7)
            c.drawString(x + 2, y - height + 3, str(value or ""))
            return y - height

        def draw_car_top_view(x, y, car_w=150, car_h=90):
            """Draw the car inspection diagram by embedding the reference image."""
            # Path to the static car inspection image
            img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "vistoria_carro.png")
            if os.path.exists(img_path):
                # drawImage: x, y is bottom-left in ReportLab
                # We receive y as top of area, so bottom-left = (x, y - car_h)
                c.drawImage(img_path, x, y - car_h, width=car_w, height=car_h, preserveAspectRatio=True, mask='auto')
            else:
                # Fallback: draw a simple placeholder rectangle
                c.saveState()
                c.setStrokeColor(colors.black)
                c.setLineWidth(0.5)
                c.rect(x, y - car_h, car_w, car_h)
                c.setFont("Helvetica", 6)
                c.drawCentredString(x + car_w / 2, y - car_h / 2, "DIAGRAMA DO VEICULO")
                c.restoreState()
            return y - car_h

        # --- LEFT COLUMN: LOCATARIO ---
        lx = margin
        lw = col_left_w
        fh = 18  # field height

        y = y_line - 4
        y = draw_section_title(y, "LOCATARIO - RENTER", sec_x=lx, sec_w=col_left_w)

        nome_cli = cliente.nome if cliente else ""
        cpf_cnpj = cliente.cpf if cliente else ""
        end_com = cliente.endereco_comercial or "" if cliente else ""
        num_com = cliente.numero_comercial or "" if cliente else ""
        bairro_com = ""
        cep_com = ""
        end_res = cliente.endereco_residencial or "" if cliente else ""
        num_res = cliente.numero_residencial or "" if cliente else ""
        bairro_res = ""
        cep_res = cliente.cep_residencial or "" if cliente else ""
        cidade = cliente.cidade_residencial or "" if cliente else ""
        estado = cliente.estado_residencial or "" if cliente else ""
        fones = cliente.telefone or "" if cliente else ""
        hotel = cliente.hotel_apartamento or "" if cliente else ""
        email = cliente.email or "" if cliente else ""
        cnh_num = cliente.numero_cnh or "" if cliente else ""
        cnh_cat = cliente.categoria_cnh or "" if cliente else ""
        cnh_val = cliente.validade_cnh.strftime("%d/%m/%Y") if cliente and cliente.validade_cnh else ""
        rg = cliente.rg or "" if cliente else ""

        # Left column fields
        y = draw_field_box(lx, y, "NOME DO CLIENTE:", nome_cli, lw, fh)
        y = draw_field_box(lx, y, "ENDERECO COMERCIAL:", end_com, lw, fh)

        # Two cols: No + Bairro + CEP
        hw = lw / 3
        yt = y
        draw_field_box(lx, yt, "No:", num_com, hw, fh)
        draw_field_box(lx + hw, yt, "BAIRRO:", bairro_com, hw, fh)
        y = draw_field_box(lx + 2 * hw, yt, "CEP:", cep_com, hw, fh)

        y = draw_field_box(lx, y, "ENDERECO RESIDENCIAL:", end_res, lw, fh)
        yt = y
        draw_field_box(lx, yt, "No:", num_res, hw, fh)
        draw_field_box(lx + hw, yt, "BAIRRO:", bairro_res, hw, fh)
        y = draw_field_box(lx + 2 * hw, yt, "CEP:", cep_res, hw, fh)

        # Cidade / Estado / Pais
        cw = lw / 3
        yt = y
        draw_field_box(lx, yt, "CIDADE:", cidade, cw, fh)
        draw_field_box(lx + cw, yt, "ESTADO:", estado, cw, fh)
        y = draw_field_box(lx + 2 * cw, yt, "PAIS:", "Brasil", cw, fh)

        y = draw_field_box(lx, y, "FONES:", fones, lw, fh)
        yt = y
        draw_field_box(lx, yt, "HOTEL:", hotel, lw * 0.7, fh)
        y = draw_field_box(lx + lw * 0.7, yt, "APTo.:", "", lw * 0.3, fh)
        y = draw_field_box(lx, y, "FONES/E-MAIL:", email, lw, fh)

        # --- IDENTIFICACAO ---
        y -= 2
        y = draw_section_title(y, "IDENTIFICACAO - IDENTIFICATION", sec_x=lx, sec_w=col_left_w)
        y = draw_field_box(lx, y, "CPF OU CNPJ:", cpf_cnpj, lw, fh)
        y = draw_field_box(lx, y, "CARTEIRA DE HABILITACAO/NUMERO:", cnh_num, lw, fh)
        y = draw_field_box(lx, y, "EMITIDA POR:", "", lw, fh)
        y = draw_field_box(lx, y, "No REG/CATEGORIA:", cnh_cat, lw, fh)
        y = draw_field_box(lx, y, "DATA DA 1a HABILITACAO/VALIDADE:", cnh_val, lw, fh)
        y = draw_field_box(lx, y, "IDENTIDADE - NUMERO:", rg, lw, fh)
        yt = y
        draw_field_box(lx, yt, "ORGAO EMISSOR:", "", lw * 0.6, fh)
        y = draw_field_box(lx + lw * 0.6, yt, "DATA DE EMISSAO:", "", lw * 0.4, fh)

        # --- CARRO ---
        y -= 2
        y = draw_section_title(y, "CARRO - CAR", sec_x=lx, sec_w=col_left_w)
        marca_tipo = "{} {}".format(veiculo.marca, veiculo.modelo) if veiculo else ""
        placa = veiculo.placa if veiculo else ""
        yt = y
        draw_field_box(lx, yt, "MARCA/TIPO:", marca_tipo, lw * 0.6, fh)
        y = draw_field_box(lx + lw * 0.6, yt, "PLACA:", placa, lw * 0.4, fh)

        # --- VISTORIA ---
        y -= 2
        y = draw_section_title(y, "VISTORIA VEICULO", sec_x=lx, sec_w=col_left_w)

        # Fuel gauge - SAIDA
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(colors.black)
        c.drawString(lx + 4, y - 10, "COMBUSTIVEL DE SAIDA")
        fuel_labels = ["RES.", "1/8", "1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "CHEIO"]
        fx = lx + 4
        fy = y - 20
        fuel_spacing = (col_left_w - 10) / len(fuel_labels)
        c.setFont("Helvetica", 4.5)
        for i, fl in enumerate(fuel_labels):
            c.drawString(fx + i * fuel_spacing, fy, fl)
        c.setLineWidth(0.5)
        c.line(fx, fy - 3, fx + fuel_spacing * len(fuel_labels), fy - 3)
        fy -= 10

        # Fuel gauge - ENTRADA
        c.setFont("Helvetica-Bold", 6)
        c.drawString(lx + 4, fy, "COMBUSTIVEL DE ENTRADA")
        fy -= 10
        c.setFont("Helvetica", 4.5)
        for i, fl in enumerate(fuel_labels):
            c.drawString(fx + i * fuel_spacing, fy, fl)
        c.line(fx, fy - 3, fx + fuel_spacing * len(fuel_labels), fy - 3)
        y = fy - 10

        # --- CHECKLIST (left side) + CAR DIAGRAM (right side) ---
        # Split the VISTORIA area: checklist on left, car on right
        checklist_w = col_left_w * 0.38
        car_area_x = lx + checklist_w + 4
        car_area_w = col_left_w - checklist_w - 8

        # Checklist items
        items = ["MACACO", "ESTEPE", "FERRAM.", "TRIANGULO", "DOCUMENTO",
                 "EXTINTOR", "CALOTAS", "TOCA-FITAS", "CD PLAYER"]
        c.setFont("Helvetica", 5.5)
        c.setFillColor(colors.black)
        check_y = y
        for item in items:
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.4)
            c.rect(lx + 4, check_y - 7, 7, 7)
            c.drawString(lx + 14, check_y - 6, item)
            check_y -= 10

        # Car top-down diagram (to the right of checklist)
        car_y_start = y
        draw_car_top_view(car_area_x, car_y_start, car_w=car_area_w, car_h=90)

        y = min(check_y, car_y_start - 90) - 4

        # Observacoes
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(colors.black)
        obs_text = contrato.observacoes or ""
        c.drawString(lx + 4, y - 4, "Observacoes: {}".format(obs_text[:60]))
        y -= 16

        # === RIGHT COLUMN ===
        rx = w / 2 + 4
        rw = col_right_w
        ry = y_line - 4

        # Check if it's a company contract (needed for data_entrada and later sections)
        eh_empresa = getattr(contrato, 'tipo', 'cliente') == 'empresa'

        # --- QUILOMETRAGEM ---
        ry_sec = ry
        c.setFont("Helvetica-Bold", 9)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawCentredString(rx + rw / 2, ry_sec - 12, "QUILOMETRAGEM")
        ry_sec -= 20

        data_saida = contrato.data_inicio.strftime("%d/%m/%Y") if contrato.data_inicio else ""
        hora_saida = contrato.hora_saida or (contrato.data_inicio.strftime("%H:%M") if contrato.data_inicio else "")
        data_entrada = contrato.data_fim.strftime("%d/%m/%Y") if contrato.data_fim else ("Indeterminado" if eh_empresa else "")
        hora_entrada = contrato.combustivel_retorno or (contrato.data_fim.strftime("%H:%M") if contrato.data_fim else "")
        km_saida = "{:,.0f}".format(float(contrato.km_inicial or 0)).replace(",", ".") if contrato.km_inicial else ""
        km_entrada = "{:,.0f}".format(float(contrato.km_final or 0)).replace(",", ".") if contrato.km_final else ""
        km_percorridos = ""
        if contrato.km_inicial and contrato.km_final:
            km_percorridos = "{:,.0f}".format(float(contrato.km_final) - float(contrato.km_inicial)).replace(",", ".")

        # Quilometragem fields (2 columns)
        qh = 16
        hw2 = rw / 2
        km_livres_str = ""
        if contrato.km_livres:
            km_livres_str = "{:,.0f} km".format(float(contrato.km_livres)).replace(",", ".")
            if contrato.valor_km_excedente:
                km_livres_str += " | R$ {:.2f}/km extra".format(float(contrato.valor_km_excedente))

        fields_km = [
            ("DATA SAIDA:", data_saida, "DATA ENTRADA:", data_entrada),
            ("HORA SAIDA:", hora_saida, "COMB. SAIDA:", contrato.combustivel_saida or ""),
            ("KM SAIDA:", km_saida, "KM ENTRADA:", km_entrada),
            ("KM PERMITIDA:", km_livres_str, "KM PERCORRIDOS:", km_percorridos),
        ]
        for f1l, f1v, f2l, f2v in fields_km:
            draw_field_box(rx, ry_sec, f1l, f1v, hw2, qh)
            ry_sec = draw_field_box(rx + hw2, ry_sec, f2l, f2v, hw2, qh)

        # --- DISCRIMINACAO pricing table ---
        ry_sec -= 4
        c.setFont("Helvetica-Bold", 9)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawCentredString(rx + rw / 2, ry_sec - 12, "DISCRIMINACAO")
        ry_sec -= 16

        # Table header
        if eh_empresa:
            cols = [rw * 0.25, rw * 0.35, rw * 0.20, rw * 0.20]
            headers = ["DISCRIMINACAO", "PERIODO DO CONTRATO", "PRECO UNIT.", "PRECO TOTAL"]
        else:
            cols = [rw * 0.35, rw * 0.15, rw * 0.25, rw * 0.25]
            headers = ["DISCRIMINACAO", "QUANT.", "PRECO UNIT.", "PRECO TOTAL"]

        c.setFont("Helvetica-Bold", 5.5)
        cx = rx
        for i, hd in enumerate(headers):
            c.rect(cx, ry_sec - 14, cols[i], 14)
            c.drawCentredString(cx + cols[i] / 2, ry_sec - 10, hd)
            cx += cols[i]
        ry_sec -= 14

        # Table rows
        valor_diaria = "R$ {:,.2f}".format(float(contrato.valor_diaria)) if contrato.valor_diaria else ""
        valor_total = "R$ {:,.2f}".format(float(contrato.valor_total)) if contrato.valor_total else ""
        
        quant_value = ""
        if contrato.data_inicio and contrato.data_fim:
            delta = contrato.data_fim - contrato.data_inicio
            dias_num = delta.days if delta.days >= 1 else 1
            if eh_empresa:
                quant_value = "{} a {}".format(
                    contrato.data_inicio.strftime("%d/%m/%Y"),
                    contrato.data_fim.strftime("%d/%m/%Y")
                )
            else:
                quant_value = str(dias_num)
        elif contrato.data_inicio and eh_empresa:
            quant_value = "{} - Indeterminado".format(contrato.data_inicio.strftime("%d/%m/%Y"))

        # Build rows - for empresa contracts, show NF period history
        rows = []
        _total_geral = 0.0
        if eh_empresa:
            # Fetch NF history for this vehicle/empresa
            _uso_for_pdf = None
            if empresa:
                _uso_for_pdf = db.query(UsoVeiculoEmpresa).filter(
                    UsoVeiculoEmpresa.empresa_id == empresa.id,
                    UsoVeiculoEmpresa.veiculo_id == target_veiculo_id,
                ).order_by(UsoVeiculoEmpresa.data_criacao.desc()).first()
            _nf_records = []
            if _uso_for_pdf:
                _nf_records = db.query(RelatorioNF).filter(
                    RelatorioNF.uso_id == _uso_for_pdf.id
                ).order_by(RelatorioNF.periodo_inicio.asc()).all()

            if _nf_records:
                _diaria_val = float(contrato.valor_diaria or 0)
                for nf in _nf_records:
                    periodo = "{} a {}".format(
                        nf.periodo_inicio.strftime("%d/%m/%Y") if nf.periodo_inicio else "",
                        nf.periodo_fim.strftime("%d/%m/%Y") if nf.periodo_fim else "",
                    )
                    _extra = float(nf.valor_total_extra or 0)
                    _valor_periodo = _diaria_val + _extra
                    _total_geral += _valor_periodo
                    rows.append((
                        periodo,
                        "{:.0f} km | +R$ {:.2f}".format(float(nf.km_percorrida or 0), _extra),
                        "R$ {:,.2f}".format(_diaria_val).replace(",", "."),
                        "R$ {:,.2f}".format(_valor_periodo).replace(",", "."),
                    ))
                rows.append((
                    "TOTAL ({} periodos)".format(len(_nf_records)),
                    "",
                    "",
                    "R$ {:,.2f}".format(_total_geral).replace(",", "."),
                ))
            else:
                rows.append(("DIARIA", quant_value, valor_diaria, valor_total))
        else:
            rows.append(("DIARIA", quant_value, valor_diaria, valor_total))

        rows += [
            ("HORA EXTRA", "", "", ""),
            ("KM EXCEDENTE", "", "", ""),
            ("SUB-TOTAL", "", "", valor_total),
            ("AVARIAS", "", "", ""),
            ("DESCONTO", "", "", ""),
        ]
        c.setFont("Helvetica", 6)
        for row_data in rows:
            cx = rx
            for i, val in enumerate(row_data):
                c.rect(cx, ry_sec - 14, cols[i], 14)
                c.drawCentredString(cx + cols[i] / 2, ry_sec - 10, str(val))
                cx += cols[i]
            ry_sec -= 14

        # TOTAL R$ - use NF total for empresa contracts if available
        _total_final_display = valor_total
        if eh_empresa and '_total_geral' in dir():
            _total_final_display = "R$ {:,.2f}".format(_total_geral).replace(",", ".")

        c.setFont("Helvetica-Bold", 7)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawString(rx + rw * 0.5, ry_sec - 12, "TOTAL R$")
        c.drawString(rx + rw * 0.75, ry_sec - 12, _total_final_display)
        ry_sec -= 20

        # --- CARTOES DE CREDITO ---
        c.setFont("Helvetica-Bold", 9)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawCentredString(rx + rw / 2, ry_sec - 12, "CARTOES DE CREDITO")
        ry_sec -= 20

        card_names = ["AMERICAN EXPRESS", "SOLO", "HIPER", "HIPER CARD", "VISA", "DINER'S"]
        c.setFont("Helvetica", 5.5)
        cx_card = rx
        cw_card = rw / len(card_names)
        for cn in card_names:
            c.rect(cx_card, ry_sec - 12, cw_card, 12)
            c.drawCentredString(cx_card + cw_card / 2, ry_sec - 9, cn)
            cx_card += cw_card
        ry_sec -= 16

        c.setFont("Helvetica", 6)
        c.drawString(rx, ry_sec - 8, "NOME: _______________________________________________________")
        ry_sec -= 14
        c.drawString(rx, ry_sec - 8, "No: __________________________________________ COD.:___________")
        ry_sec -= 14
        c.drawString(rx, ry_sec - 8, "PRE/AUT.:__________________ VAL.:_____________ R$:_____________")
        ry_sec -= 18

        # --- AVISO MULTAS ---
        c.setFont("Helvetica-Bold", 6)
        c.rect(rx, ry_sec - 20, rw, 20, fill=0)
        c.drawCentredString(rx + rw / 2, ry_sec - 9, "EVENTUAIS MULTAS SERAO COBRADAS POSTERIORMENTE,")
        c.drawCentredString(rx + rw / 2, ry_sec - 17, "DECLARO-ME CIENTE DO CONTEUDO DESTE CONTRATO")
        ry_sec -= 24

        # --- Terms text (justified using Paragraph) ---
        from reportlab.platypus import Paragraph as RLParagraph
        from reportlab.lib.styles import ParagraphStyle as RLParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER as TA_C

        terms_style = RLParagraphStyle(
            "TermsText", fontName="Helvetica", fontSize=5.5,
            leading=7, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=0,
        )
        terms_center = RLParagraphStyle(
            "TermsCenter", fontName="Helvetica-Bold", fontSize=6,
            leading=8, alignment=TA_C, spaceBefore=0, spaceAfter=0,
        )
        title_center = RLParagraphStyle(
            "TitleCenter", fontName="Helvetica-Bold", fontSize=8,
            leading=10, alignment=TA_C, spaceBefore=0, spaceAfter=0,
        )
        multa_style = RLParagraphStyle(
            "MultaText", fontName="Helvetica", fontSize=5.5,
            leading=7, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=0,
        )

        terms_text = (
            "O cliente e responsavel por todas as infracoes de transito, "
            "autorizando a locadora debitar despesas extras em seu cartao de credito. "
            "Costumeris liable for all parking and traffic violations. "
            "Terminantemente proibido o trafego de carro em dunas e beira-mar, "
            "caso seja contatado incidira multa de R$ 1.000,00 (hum mil reais) e "
            "rescisao de contrato por parte da locadora. "
            "Depois de ter lido devidamente os termos e condicoes do contrato "
            "no anveso e verso, concordo expressamente, firmo presente."
        )
        p = RLParagraph(terms_text, terms_style)
        pw, ph = p.wrap(rw - 4, 200)
        p.drawOn(c, rx + 2, ry_sec - ph)
        ry_sec -= ph + 6

        # Assinatura do cliente
        c.drawCentredString(rx + rw / 2, ry_sec, "___________________________________________________________")
        ry_sec -= 10
        p = RLParagraph("Assinatura do Cliente", terms_center)
        pw, ph = p.wrap(rw, 20)
        p.drawOn(c, rx, ry_sec - ph)
        ry_sec -= ph + 8

        # --- TERMOS DE DECLARACAO DE MULTAS ---
        p = RLParagraph("TERMOS DE DECLARACAO DE MULTAS", title_center)
        pw, ph = p.wrap(rw, 20)
        p.drawOn(c, rx, ry_sec - ph)
        ry_sec -= ph + 6

        multa_text1 = (
            "Declaro conhecer a legislacao em vigor relativo ao novo Codigo "
            "de Transito Brasileiro e me responsabilizo inteiramente por quais quer "
            "penalidades decorrentes das infracoes por mim cometidas na "
            "conducao do veiculo locado, quer pecuniarias ou pontuacao, que "
            "serao informadas por MPCAR'S. A autoridade de transito, para que "
            "estas respectivas notificacoes e recibos de pagamento das multas, "
            "conforme verso e anverso deste contrato."
        )
        p = RLParagraph(multa_text1, multa_style)
        pw, ph = p.wrap(rw - 4, 200)
        p.drawOn(c, rx + 2, ry_sec - ph)
        ry_sec -= ph + 6

        multa_text2 = (
            "O Locatario, desde ja constitui a LOCADORA sua bastante "
            "procuradora para fim especifico de atender resolucao no 72/98 do "
            "CONTRAN ficando a LOCADORA autorizada a assinar, em nome deste "
            "LOCATARIO e campo correspondente e assinatura do condutor "
            "infrator, no formulario de identificacao. Em caso de infracao de transito."
        )
        p = RLParagraph(multa_text2, multa_style)
        pw, ph = p.wrap(rw - 4, 200)
        p.drawOn(c, rx + 2, ry_sec - ph)
        ry_sec -= ph + 6

        multa_text3 = "Fica ainda estabelecido, que esta autorizacao so sera valida, se o"
        p = RLParagraph(multa_text3, multa_style)
        pw, ph = p.wrap(rw - 4, 200)
        p.drawOn(c, rx + 2, ry_sec - ph)
        ry_sec -= ph + 4

        c.setFont("Helvetica", 5.5)
        c.drawString(rx + 2, ry_sec, "Data e Hora da Saida: ____________________________________")
        ry_sec -= 14
        c.drawString(rx + 2, ry_sec, "______________________________________________________")

        # --- FOOTER PAGE 1 ---
        c.setFont("Helvetica", 5.5)
        c.drawCentredString(w / 2, margin - 5, "RUA MANOEL ALEXANDRE 1048 - LJ 02 - EDIFICIO COMERCIAL E RESIDENCIAL")
        c.drawCentredString(w / 2, margin - 13, "PRINCESINHA DO OESTE - CEP 59900-000 - PAU DOS FERROS-RN")
        c.drawCentredString(w / 2, margin - 21, "CNPJ.: 52.471.526/0001-53  84 99911-0504")

        # ============ PAGE 2: TERMS AND CONDITIONS ============
        c.showPage()

        # Two-column layout for terms
        col1_x = margin
        col2_x = w / 2 + 8
        col_w = w / 2 - margin - 8
        ty = h - margin

        clause_style = RLParagraphStyle(
            "ClauseText", fontName="Helvetica", fontSize=6,
            leading=7.5, alignment=TA_JUSTIFY, spaceBefore=0, spaceAfter=2,
        )
        clause_bold = RLParagraphStyle(
            "ClauseBold", fontName="Helvetica-Bold", fontSize=7,
            leading=9, alignment=TA_C, spaceBefore=0, spaceAfter=0,
        )

        clausulas_col1_text = (
            "Carroceria, com hodometro instalado pelo fabricante, "
            "lacrado, em boas condicoes de utilizacao, encontra-se o veiculo locado;\n\n"
            "<b>1)</b> caracterizado no anverso deste documento, nos quadros "
            "respectivos, O(A) LOCATARIO(A) recebe e aceita com plenos conhecimentos "
            "o referido veiculo e respectivos acessorios, conforme relacao em anexo e "
            "se obriga a indenizar totalmente a LOCADORA no momento de entrega do "
            "veiculo, pelos acessorios eventualmente faltante, ao preco vigente no mercado.\n\n"
            "<b>2)</b> O preco de aluguel do veiculo locado sera declarado no anverso deste "
            "contrato calculado com base na tabela de tarifas da LOCADORA da qual o "
            "LOCATARIO (A) tem pleno conhecimento. Ficara ao(s) cargo(s) do(a) "
            "LOCATARIO(A) deste contrato; b) uma vez efetuada a devolucao do veiculo "
            "locado a LOCADORA, estabelecera o valor do aluguel, nos termos do presente "
            "contrato, precedendo ao desconto da quantia ja paga a titulo de adiantamento, "
            "devendo o(a) LOCATARIO(A) efetuar a LOCADORA o pagamento da diferenca "
            "resultante; c) por ocasiao da devolucao do veiculo, o(a) LOCATARIO(A) se "
            "compromete a pagar a LOCADORA O imposto sobre servicos incidentes sobre o "
            "custo total do aluguel e das tarifas adicionais; d) na falta de pagamento pontual "
            "dos servicos prestados ao LOCATARIO(A), ficara este(a) sujeito(a) ao pagamento "
            "de multa equivalente a 20% (vinte por cento) sobre o valor devido, acrescido de "
            "juros de 25% (vinte e cinco por cento) ao mes.\n\n"
            "<b>3)</b> O prazo de vigencia do presente contrato esta indicado no quadro "
            "respectivo, devendo o(a) LOCATARIO(A) efetuar a devolucao do veiculo no dia, "
            "hora e local estipulado, e somente podera ser prorrogado com anuencia da "
            "LOCADORA, por escrito no anverso do presente contrato.\n\n"
            "<b>4)</b> Findo o prazo contratual devera o(a) LOCATARIO(A) restituir o veiculo a "
            "LOCADORA, no mesmo estado em que recebeu, excluindo-se apenas o desgaste "
            "normal dos pneumaticos.\n\n"
            "<b>5)</b> A nao devolucao do veiculo locado por parte do(a) LOCATARIO(A), "
            "implicara na pratica de apropriacao indebita, ficando o(a) mesmo(a) sujeito(a) "
            "as leis penais, podendo a LOCADORA promover contra o(a) LOCATARIO(A) a "
            "competente representacao junto as autoridades policiais, para abertura de "
            "inquerito policial, bem como a retomada do veiculo locado.\n\n"
            "<b>6)</b> Todas e quaisquer despesas que se fizerem necessarias, para a retomada "
            "e posse do veiculo locado, inclusive judiciais e extrajudiciais, bem como aquelas "
            "decorrentes de transporte e remocao do mesmo. Correcao por conta exclusiva "
            "do(a) LOCATARIO(A).\n\n"
            "<b>7)</b> A LOCADORA podera propor contra o(a) LOCATARIO(A) as competentes "
            "acoes civeis que se fizerem necessarias.\n\n"
            "<b>8)</b> O veiculo locado destinar-se-a unico e exclusivo ao transporte de pessoas "
            "e a referido veiculo so podera ser conduzido pelo(a) LOCATARIO(A), ou, sob sua "
            "responsabilidade, pelo motorista ou motoristas por ele indicados, desde que estejam "
            "qualificados no anverso deste mesmo contrato.\n\n"
            "<b>9)</b> O(A) LOCATARIO(A) se obriga nao utilizar o veiculo locado em outro "
            "Estado sem o consentimento por da LOCADORA.\n\n"
            "<b>10)</b> Sao obrigacoes do(a) LOCATARIO(A), bem como do(s) motoristas "
            "indicados pelo LOCATARIO:\n"
            "a) conduzir o veiculo locado durante a locacao, munido da documentacao legal "
            "correspondente, e expedida pelas autoridades competentes, que o autorizem a "
            "conduzir o veiculo locado;\n"
            "b) nao fazendo uso do veiculo para fins lucrativo;"
        )

        p1 = RLParagraph(clausulas_col1_text, clause_style)
        pw1, ph1 = p1.wrap(col_w, h - 2 * margin - 60)
        p1.drawOn(c, col1_x, ty - ph1)
        ty_bottom_col1 = ty - ph1

        clausulas_col2_text = (
            "c) nao sub-locar o veiculo;\n"
            "d) obedecer as leis de transito, Federal, Estadual e Municipal;\n"
            "I) o pagamento das multas Impostas por quaisquer transgressoes a "
            "regulamentacao de transito ou qualquer outra regulamentacao (autorizando "
            "a locadora a debitar em cartao de credito); e ou emitir duplicata;\n"
            "m) responder por todos os atos licitos efetuados com veiculo no interior do mesmo;\n"
            "n) reembolsar a LOCADORA os correspondentes aos combustiveis faltante no "
            "caso do veiculo locado ser devolvido com menor quantidade de combustivel que "
            "havia no momento da entrega do veiculo a o(a) LOCATARIO(A).\n\n"
            "<b>11)</b> No caso de acidente ou desaparecimento do veiculo locado, durante o "
            "prazo de vigencia do presente contrato, o(a) LOCATARIO(A), se obriga a comunicar "
            "imediatamente o evento as AUTORIDADES competentes, apresentando o comprovante "
            "deste comunicado a LOCADORA, sob pena de ser responsabilizado(a) pelo abandono "
            "do veiculo, e:\n"
            "a) no caso de acidente ou qualquer outro incidente que venha a ser atribuido ao "
            "LOCATARIO(A), como consequencia do nao cumprimento das disposicoes contidas "
            "neste contrato o(a) LOCATARIO(A) reembolsara a LOCADORA o aluguel correspondente "
            "ao periodo em que, uma vez ultrapassado o prazo de locacao, o veiculo locado nao se "
            "encontre a disposicao da LOCADORA, bem como multa equivalente a 20% (vinte por "
            "sobre o valor devido, acrescido de juros de 25% (vinte e cinco por cento) ao mes.\n\n"
            "<b>12)</b> Se durante o prazo de locacao, ocorrer algum defeito no marcador de "
            "quilometragem (hodometro) o(a) LOCATARIO(A) se compromete a avisar de imediato "
            "a LOCADORA, para que se proceda ao conserto do referido defeito; neste caso fica, "
            "desde ja estabelecido entre as partes que a tarifa de quilometragem sera calculada "
            "com base na media de 1.000 (hum mil quilometros por dia).\n\n"
            "<b>13)</b> A LOCADORA nao se responsabiliza pelos objetos pessoais esquecidos "
            "pelo(a) LOCATARIO(A) ou seus passageiros no Interior do veiculo ou em seus "
            "estabelecimentos, nem pelos danos ou depreciacao sofrida por objetos transportados "
            "em seus veiculos.\n\n"
            "<b>14)</b> Este contrato se encerra:\n"
            "a) por haver expirado o prazo fixado no mesmo;\n"
            "b) por acordo expresso entre as partes;\n"
            "c) por rescisao;\n"
            "d) por perdas, danos ou defeitos desconhecidos que Inutilizem o veiculo aludido, "
            "ou pela destruicao do mesmo;\n"
            "e) por morte do(a) LOCATARIO(A).\n\n"
            "<b>15)</b> Dar-se-a a rescisao deste contrato, na hipotese do nao cumprimento por "
            "parte do(a) LOCATARIO(A) das obrigacoes pactuadas neste instrumento."
        )

        ry2 = h - margin
        p2 = RLParagraph(clausulas_col2_text, clause_style)
        pw2, ph2 = p2.wrap(col_w, h - 2 * margin - 60)
        p2.drawOn(c, col2_x, ry2 - ph2)
        ty_bottom_col2 = ry2 - ph2

        # Signatures at bottom
        sig_y = min(ty_bottom_col1, ty_bottom_col2) - 20
        if sig_y < 100:
            sig_y = 100

        c.setLineWidth(0.5)
        sig_line_w = col_w - 10

        # Left signatures
        c.line(col1_x, sig_y, col1_x + sig_line_w, sig_y)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(col1_x + sig_line_w / 2, sig_y - 10, "LOCATARIO")

        c.line(col1_x, sig_y - 30, col1_x + sig_line_w, sig_y - 30)
        c.drawCentredString(col1_x + sig_line_w / 2, sig_y - 40, "LOCADORA")

        # Right signatures
        c.line(col2_x, sig_y, col2_x + sig_line_w, sig_y)
        c.drawCentredString(col2_x + sig_line_w / 2, sig_y - 10, "TESTEMUNHA 1")

        c.line(col2_x, sig_y - 30, col2_x + sig_line_w, sig_y - 30)
        c.drawCentredString(col2_x + sig_line_w / 2, sig_y - 40, "TESTEMUNHA 2")

        # === PAGE 3: NF HISTORY (only for empresa contracts) ===
        if contrato.tipo == "empresa" and empresa:
            uso = db.query(UsoVeiculoEmpresa).filter(
                UsoVeiculoEmpresa.contrato_id == contrato_id,
                UsoVeiculoEmpresa.veiculo_id == target_veiculo_id,
            ).first()
            if not uso:
                uso = db.query(UsoVeiculoEmpresa).filter(
                    UsoVeiculoEmpresa.empresa_id == empresa.id,
                    UsoVeiculoEmpresa.veiculo_id == target_veiculo_id,
                ).order_by(UsoVeiculoEmpresa.data_criacao.desc()).first()

            nf_records = []
            if uso:
                nf_records = db.query(RelatorioNF).filter(
                    RelatorioNF.uso_id == uso.id
                ).order_by(RelatorioNF.periodo_inicio.asc()).all()

            if nf_records:
                c.showPage()
                y = h - margin

                c.setFont("Helvetica-Bold", 16)
                c.drawString(margin, y - 10, "HISTORICO DE PERIODOS - NOTA FISCAL")
                y -= 30

                c.setFont("Helvetica", 8)
                c.drawString(margin, y, "Empresa: {}".format(empresa.nome))
                y -= 12
                c.drawString(margin, y, "CNPJ: {}".format(empresa.cnpj or ""))
                y -= 12
                placa_str = veiculo.placa if veiculo else ""
                modelo_str = "{} {}".format(veiculo.marca, veiculo.modelo) if veiculo else ""
                c.drawString(margin, y, "Veiculo: {} - {}".format(placa_str, modelo_str))
                y -= 12
                c.drawString(margin, y, "KM Permitida (Franquia): {} km".format(uso.km_referencia or 0))
                y -= 20

                # Table header
                c.setFont("Helvetica-Bold", 7)
                col_x = [margin, margin + 80, margin + 160, margin + 240, margin + 320, margin + 410]
                headers = ["Periodo Inicio", "Periodo Fim", "KM Percorrida", "KM Excedente", "Valor Extra", "Data Emissao"]
                for i, hdr in enumerate(headers):
                    c.drawString(col_x[i], y, hdr)
                y -= 2
                c.setLineWidth(0.5)
                c.line(margin, y, w - margin, y)
                y -= 10

                c.setFont("Helvetica", 7)
                total_km = 0
                total_excedente = 0
                total_valor = 0
                for nf in nf_records:
                    if y < 60:
                        c.showPage()
                        y = h - margin
                        c.setFont("Helvetica", 7)
                    c.drawString(col_x[0], y, nf.periodo_inicio.strftime("%d/%m/%Y") if nf.periodo_inicio else "")
                    c.drawString(col_x[1], y, nf.periodo_fim.strftime("%d/%m/%Y") if nf.periodo_fim else "")
                    c.drawString(col_x[2], y, "{:,.1f} km".format(nf.km_percorrida or 0))
                    c.drawString(col_x[3], y, "{:,.1f} km".format(nf.km_excedente or 0))
                    c.drawString(col_x[4], y, "R$ {:,.2f}".format(float(nf.valor_total_extra or 0)))
                    c.drawString(col_x[5], y, nf.data_criacao.strftime("%d/%m/%Y") if nf.data_criacao else "")
                    total_km += float(nf.km_percorrida or 0)
                    total_excedente += float(nf.km_excedente or 0)
                    total_valor += float(nf.valor_total_extra or 0)
                    y -= 12

                # Totals
                y -= 5
                c.setLineWidth(0.5)
                c.line(margin, y + 8, w - margin, y + 8)
                c.setFont("Helvetica-Bold", 7)
                c.drawString(col_x[0], y, "TOTAL ({} periodos)".format(len(nf_records)))
                c.drawString(col_x[2], y, "{:,.1f} km".format(total_km))
                c.drawString(col_x[3], y, "{:,.1f} km".format(total_excedente))
                c.drawString(col_x[4], y, "R$ {:,.2f}".format(total_valor))

        c.save()
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
    def generate_relatorio_financeiro_pdf(
        db: Session, data_inicio: str, data_fim: str,
        tipo: str = None, status_filter: str = None, categoria: str = None,
        veiculo_id: int = None, search: str = None,
    ) -> BytesIO:
        """Generate financial report PDF using ALL financial data sources."""
        from app.models import (
            Contrato, Cliente, Veiculo, DespesaContrato, DespesaVeiculo,
            DespesaLoja, Manutencao, Seguro, IpvaRegistro, Multa,
            LancamentoFinanceiro, Empresa, UsoVeiculoEmpresa,
        )
        from app.models import RelatorioNF

        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        empresa_info = _get_empresa_info(db)

        # ── Collect ALL records (same logic as list_financeiro) ──
        all_records = []

        # 1. Contratos PF (receita)
        contratos = db.query(Contrato).all()
        for c in contratos:
            if str(c.tipo or "").lower() == "empresa":
                continue
            cliente = db.query(Cliente).filter(Cliente.id == c.cliente_id).first()
            all_records.append({
                "data": c.data_criacao.isoformat() if c.data_criacao else None,
                "tipo": "receita",
                "categoria": "Locacao",
                "descricao": "Contrato #{} - {}".format(c.numero, cliente.nome if cliente else "N/A"),
                "valor": float(c.valor_total or 0),
                "status": "pago" if c.status == "finalizado" else "pendente",
                "veiculo_id": c.veiculo_id,
            })

        # 2. NF empresa (receita)
        for nf in db.query(RelatorioNF).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == nf.veiculo_id).first()
            empresa = db.query(Empresa).filter(Empresa.id == nf.empresa_id).first() if nf.empresa_id else None
            periodo = ""
            if nf.periodo_inicio:
                periodo = nf.periodo_inicio.strftime("%d/%m/%y")
                if nf.periodo_fim:
                    periodo += " a " + nf.periodo_fim.strftime("%d/%m/%y")
            all_records.append({
                "data": nf.data_criacao.isoformat() if nf.data_criacao else None,
                "tipo": "receita",
                "categoria": "Faturamento empresa",
                "descricao": "NF {} {} | {}".format(
                    veiculo.placa if veiculo else "",
                    periodo,
                    empresa.nome if empresa else "",
                ).strip(),
                "valor": float(nf.valor_total_periodo or 0),
                "status": "pago" if nf.pago else "pendente",
                "veiculo_id": nf.veiculo_id,
            })

        # 3. Despesas de Contrato
        for d in db.query(DespesaContrato).all():
            all_records.append({
                "data": d.data_registro.isoformat() if d.data_registro else None,
                "tipo": "despesa",
                "categoria": d.tipo or "Contrato",
                "descricao": d.descricao or "",
                "valor": float(d.valor or 0),
                "status": "pago",
                "veiculo_id": None,
            })

        # 4. Despesas de Veiculo
        for d in db.query(DespesaVeiculo).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == d.veiculo_id).first() if d.veiculo_id else None
            all_records.append({
                "data": d.data.isoformat() if d.data else None,
                "tipo": "despesa",
                "categoria": d.tipo or "Veiculo",
                "descricao": "{} | {}".format(d.descricao or "", veiculo.placa if veiculo else "").strip(" |"),
                "valor": float(d.valor or 0),
                "status": "pago",
                "veiculo_id": d.veiculo_id,
            })

        # 5. Despesas de Loja
        for d in db.query(DespesaLoja).all():
            all_records.append({
                "data": d.data.isoformat() if d.data else None,
                "tipo": "despesa",
                "categoria": d.categoria or "Loja",
                "descricao": d.descricao or "",
                "valor": float(d.valor or 0),
                "status": "pago",
                "veiculo_id": None,
            })

        # 6. Manutencoes
        for m in db.query(Manutencao).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == m.veiculo_id).first() if m.veiculo_id else None
            data = m.data_realizada or m.updated_at or m.data_criacao
            all_records.append({
                "data": data.isoformat() if data else None,
                "tipo": "despesa",
                "categoria": "Manutencao",
                "descricao": "{} | {}".format(m.descricao or "", veiculo.placa if veiculo else "").strip(" |"),
                "valor": float(m.custo or 0),
                "status": "pago" if m.status == "concluida" else "pendente",
                "veiculo_id": m.veiculo_id,
            })

        # 7. Seguros
        for s in db.query(Seguro).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == s.veiculo_id).first() if s.veiculo_id else None
            all_records.append({
                "data": s.data_inicio.isoformat() if s.data_inicio else None,
                "tipo": "despesa",
                "categoria": "Seguro",
                "descricao": "{} | {}".format(s.seguradora or "Seguro", veiculo.placa if veiculo else "").strip(" |"),
                "valor": float(s.valor or 0),
                "status": "pago" if s.status == "ativo" else "pendente",
                "veiculo_id": s.veiculo_id,
            })

        # 8. IPVA
        for ip in db.query(IpvaRegistro).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == ip.veiculo_id).first() if ip.veiculo_id else None
            data = ip.data_pagamento or ip.data_vencimento
            all_records.append({
                "data": data.isoformat() if data else None,
                "tipo": "despesa",
                "categoria": "IPVA",
                "descricao": "IPVA {} | {}".format(ip.ano_referencia or "", veiculo.placa if veiculo else "").strip(" |"),
                "valor": float(ip.valor_ipva or ip.valor_pago or 0),
                "status": "pago" if ip.status == "pago" else "pendente",
                "veiculo_id": ip.veiculo_id,
            })

        # 9. Multas
        for ml in db.query(Multa).all():
            veiculo = db.query(Veiculo).filter(Veiculo.id == ml.veiculo_id).first() if ml.veiculo_id else None
            data = ml.data_pagamento or ml.data_infracao
            all_records.append({
                "data": data.isoformat() if data else None,
                "tipo": "despesa",
                "categoria": "Multa",
                "descricao": "{} | {}".format(ml.descricao or "Multa", veiculo.placa if veiculo else "").strip(" |"),
                "valor": float(ml.valor or 0),
                "status": "pago" if ml.status == "pago" else "pendente",
                "veiculo_id": ml.veiculo_id,
            })

        # 10. Lancamentos manuais
        for lf in db.query(LancamentoFinanceiro).all():
            all_records.append({
                "data": lf.data.isoformat() if lf.data else None,
                "tipo": lf.tipo or "despesa",
                "categoria": lf.categoria or "Outros",
                "descricao": lf.descricao or "",
                "valor": float(lf.valor or 0),
                "status": lf.status or "pendente",
                "veiculo_id": None,
            })

        # ── Apply filters ──
        def in_period(date_str):
            if not date_str:
                return True
            try:
                d = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                return di <= d <= df
            except Exception:
                return True

        records = [r for r in all_records if in_period(r["data"])]

        if tipo and tipo != "todos":
            records = [r for r in records if r["tipo"] == tipo]
        if status_filter and status_filter != "todos":
            records = [r for r in records if r["status"] == status_filter]
        if categoria:
            cat_lower = categoria.lower()
            records = [r for r in records if cat_lower in (r.get("categoria") or "").lower()]
        if veiculo_id:
            records = [r for r in records if str(r.get("veiculo_id") or "") == str(veiculo_id)]
        if search:
            s = search.lower()
            records = [r for r in records if s in (r.get("descricao") or "").lower() or s in (r.get("categoria") or "").lower()]

        records.sort(key=lambda x: x.get("data") or "", reverse=True)

        # ── Calculate totals ──
        receitas = [r for r in records if r["tipo"] == "receita"]
        despesas = [r for r in records if r["tipo"] == "despesa"]
        receita_total = sum(r["valor"] for r in receitas)
        despesa_total = sum(r["valor"] for r in despesas)
        lucro = receita_total - despesa_total

        # Group despesas by category
        desp_por_cat = {}
        for r in despesas:
            cat = r.get("categoria") or "Outros"
            desp_por_cat[cat] = desp_por_cat.get(cat, 0) + r["valor"]

        # ── Build PDF ──
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
        story = []
        styles = getSampleStyleSheet()

        filtros_desc = "Periodo: {} a {}".format(di.strftime("%d/%m/%Y"), df.strftime("%d/%m/%Y"))
        filtros_extras = []
        if tipo and tipo != "todos":
            filtros_extras.append("Tipo: {}".format(tipo.capitalize()))
        if status_filter and status_filter != "todos":
            filtros_extras.append("Status: {}".format(status_filter.capitalize()))
        if categoria:
            filtros_extras.append("Categoria: {}".format(categoria))
        if veiculo_id:
            v = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
            if v:
                filtros_extras.append("Veiculo: {} {}".format(v.placa, v.modelo))
        if filtros_extras:
            filtros_desc += " | " + " | ".join(filtros_extras)
        _add_header(story, styles, "RELATORIO FINANCEIRO COMPLETO", filtros_desc, empresa_info)

        # Summary table
        summary_data = [
            ["Metrica", "Valor"],
            ["Total de Receitas", "R$ {:,.2f}".format(receita_total)],
            ["Total de Despesas", "R$ {:,.2f}".format(despesa_total)],
            ["Lucro Liquido", "R$ {:,.2f}".format(lucro)],
            ["Margem de Lucro", "{:.1f}%".format((lucro / receita_total * 100) if receita_total > 0 else 0)],
            ["Total de Registros", str(len(records))],
        ]
        story.append(_styled_table(summary_data, col_widths=[4*inch, 3*inch]))
        story.append(Spacer(1, 12))

        # Despesas por categoria
        if desp_por_cat:
            sec_cat = ParagraphStyle("SC", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#dc2626"), spaceAfter=6)
            story.append(Paragraph("<b>DESPESAS POR CATEGORIA</b>", sec_cat))
            cat_rows = [["Categoria", "Valor", "% do Total"]]
            for cat, val in sorted(desp_por_cat.items(), key=lambda x: -x[1]):
                pct = (val / despesa_total * 100) if despesa_total > 0 else 0
                cat_rows.append([cat, "R$ {:,.2f}".format(val), "{:.1f}%".format(pct)])
            cat_rows.append(["TOTAL", "R$ {:,.2f}".format(despesa_total), "100%"])
            story.append(_styled_table(cat_rows, col_widths=[5*cm, 5*cm, 3*cm]))
            story.append(Spacer(1, 12))

        # Receitas detail
        if receitas:
            sec_rec = ParagraphStyle("SR", parent=styles["Heading2"], fontSize=12, textColor=PRIMARY, spaceAfter=6)
            story.append(Paragraph("<b>DETALHAMENTO DE RECEITAS ({} registros)</b>".format(len(receitas)), sec_rec))
            rev_rows = [["Data", "Categoria", "Descricao", "Valor", "Status"]]
            for r in receitas:
                data_fmt = ""
                if r["data"]:
                    try:
                        data_fmt = datetime.fromisoformat(r["data"].replace("Z", "+00:00")).strftime("%d/%m/%y")
                    except Exception:
                        data_fmt = str(r["data"])[:10]
                desc = (r["descricao"] or "")[:35]
                if len(r["descricao"] or "") > 35:
                    desc += ".."
                rev_rows.append([
                    data_fmt,
                    (r["categoria"] or "")[:15],
                    desc,
                    "R$ {:,.2f}".format(r["valor"]),
                    r["status"] or "",
                ])
            rev_rows.append(["", "", "TOTAL", "R$ {:,.2f}".format(receita_total), ""])
            story.append(_styled_table(rev_rows, col_widths=[2*cm, 3*cm, 5.5*cm, 3.5*cm, 2*cm]))
            story.append(Spacer(1, 12))

        # Despesas detail
        if despesas:
            sec_desp = ParagraphStyle("SD", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#dc2626"), spaceAfter=6)
            story.append(Paragraph("<b>DETALHAMENTO DE DESPESAS ({} registros)</b>".format(len(despesas)), sec_desp))
            desp_rows = [["Data", "Categoria", "Descricao", "Valor", "Status"]]
            for r in despesas:
                data_fmt = ""
                if r["data"]:
                    try:
                        data_fmt = datetime.fromisoformat(r["data"].replace("Z", "+00:00")).strftime("%d/%m/%y")
                    except Exception:
                        data_fmt = str(r["data"])[:10]
                desc = (r["descricao"] or "")[:35]
                if len(r["descricao"] or "") > 35:
                    desc += ".."
                desp_rows.append([
                    data_fmt,
                    (r["categoria"] or "")[:15],
                    desc,
                    "R$ {:,.2f}".format(r["valor"]),
                    r["status"] or "",
                ])
            desp_rows.append(["", "", "TOTAL", "R$ {:,.2f}".format(despesa_total), ""])
            story.append(_styled_table(desp_rows, col_widths=[2*cm, 3*cm, 5.5*cm, 3.5*cm, 2*cm]))

        _add_footer(story, styles)
        doc.build(story)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_relatorio_receitas_pdf(db: Session, data_inicio: str, data_fim: str) -> BytesIO:
        """Generate revenue-only report PDF (separate from full financial report)."""
        di = datetime.strptime(data_inicio, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        empresa_info = _get_empresa_info(db)

        contratos = db.query(Contrato).filter(Contrato.data_criacao >= di, Contrato.data_criacao <= df).all()
        receita_total = sum(float(c.valor_total or 0) for c in contratos)
        ativos = sum(1 for c in contratos if c.status == "ativo")
        finalizados = sum(1 for c in contratos if c.status == "finalizado")
        receita_ativos = sum(float(c.valor_total or 0) for c in contratos if c.status == "ativo")
        receita_finalizados = sum(float(c.valor_total or 0) for c in contratos if c.status == "finalizado")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
        story = []
        styles = getSampleStyleSheet()
        sec_style = ParagraphStyle("S", parent=styles["Heading2"], fontSize=13, textColor=SUCCESS, spaceAfter=8)

        _add_header(story, styles, "RELATORIO DE RECEITAS", "Periodo: {} a {}".format(di.strftime("%d/%m/%Y"), df.strftime("%d/%m/%Y")), empresa_info)

        # Summary
        summary_data = [
            ["Metrica", "Valor"],
            ["Total de Contratos", str(len(contratos))],
            ["Contratos Ativos", str(ativos)],
            ["Contratos Finalizados", str(finalizados)],
            ["Receita Contratos Ativos", "R$ {:,.2f}".format(receita_ativos)],
            ["Receita Contratos Finalizados", "R$ {:,.2f}".format(receita_finalizados)],
            ["Receita Total", "R$ {:,.2f}".format(receita_total)],
        ]
        story.append(_styled_table(summary_data, col_widths=[4*inch, 3*inch]))
        story.append(Spacer(1, 20))

        # Detail by contract
        if contratos:
            story.append(Paragraph("<b>DETALHAMENTO POR CONTRATO</b>", sec_style))
            rev_rows = [["Contrato", "Cliente", "Veiculo", "Período Utilizado/Faturado", "Valor Diaria", "Valor Total", "Status"]]
            for c in contratos:
                cliente = db.query(Cliente).filter(Cliente.id == c.cliente_id).first()
                veiculo = db.query(Veiculo).filter(Veiculo.id == c.veiculo_id).first()
                dias = 0
                if c.data_inicio and c.data_fim:
                    dias = (c.data_fim - c.data_inicio).days
                    if dias < 1:
                        dias = 1
                rev_rows.append([
                    c.numero,
                    (cliente.nome[:18] + "..") if cliente and len(cliente.nome) > 20 else (cliente.nome if cliente else "N/A"),
                    veiculo.placa if veiculo else "N/A",
                    str(dias),
                    "R$ {:,.2f}".format(float(c.valor_diaria or 0)),
                    "R$ {:,.2f}".format(float(c.valor_total or 0)),
                    c.status,
                ])
            story.append(_styled_table(rev_rows, col_widths=[1.8*cm, 3*cm, 2*cm, 1.5*cm, 2.2*cm, 2.5*cm, 2*cm]))

            # Receita calculada vs registrada
            story.append(Spacer(1, 16))
            story.append(Paragraph("<b>VERIFICACAO DE VALORES</b>", sec_style))
            check_rows = [["Contrato", "Dias x Diaria (Calculado)", "Valor Total (Registrado)", "Diferenca"]]
            for c in contratos:
                dias = 0
                if c.data_inicio and c.data_fim:
                    dias = (c.data_fim - c.data_inicio).days
                    if dias < 1:
                        dias = 1
                calculado = dias * float(c.valor_diaria or 0)
                registrado = float(c.valor_total or 0)
                diff = registrado - calculado
                check_rows.append([
                    c.numero,
                    "R$ {:,.2f}".format(calculado),
                    "R$ {:,.2f}".format(registrado),
                    "R$ {:,.2f}".format(diff) if abs(diff) > 0.01 else "OK",
                ])
            story.append(_styled_table(check_rows, col_widths=[3*cm, 4.5*cm, 4.5*cm, 3*cm]))
        else:
            story.append(Paragraph("Nenhuma receita encontrada no periodo.", styles["Normal"]))

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
        # Filter DespesaLoja by month/year within the date range
        all_desp_loja = db.query(DespesaLoja).all()
        desp_loja = [d for d in all_desp_loja if di.year <= d.ano <= df.year and (
            (d.ano == di.year and d.ano == df.year and di.month <= d.mes <= df.month) or
            (d.ano == di.year and d.ano < df.year and d.mes >= di.month) or
            (d.ano > di.year and d.ano < df.year) or
            (d.ano == df.year and d.ano > di.year and d.mes <= df.month)
        )]

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
