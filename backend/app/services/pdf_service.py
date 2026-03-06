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
        """Generate contract PDF matching the MPCARS official template with vehicle inspection diagram."""
        from reportlab.pdfgen import canvas as pdfcanvas

        contrato = db.query(Contrato).filter(Contrato.id == contrato_id).first()
        if not contrato:
            raise ValueError("Contrato nao encontrado")

        cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()
        veiculo = db.query(Veiculo).filter(Veiculo.id == contrato.veiculo_id).first()
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

        def draw_section_title(y, title):
            c.setFillColor(colors.HexColor("#1a1a1a"))
            c.setFont("Helvetica-Bold", 9)
            box_h = 16
            c.rect(margin, y - box_h, w - 2 * margin, box_h, fill=0)
            c.drawCentredString(w / 2, y - box_h + 4, title)
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

        def draw_car_inspection_diagram(x, y, width=200, height=120):
            """Draw a top-down view of a sedan car for inspection damage marking."""
            c.saveState()
            c.setStrokeColor(colors.black)
            c.setLineWidth(0.8)

            # Title
            c.setFont("Helvetica-Bold", 6)
            c.setFillColor(colors.black)
            c.drawString(x, y, "DIAGRAMA DE VISTORIA")

            # --- TOP-DOWN VIEW (bird's eye sedan) ---
            cx = x + width / 2  # center x
            cy = y - 55  # center y
            bw = 50  # body width
            bh = 90  # body height (length of car)

            # Car body outline using path
            p = c.beginPath()
            # Start bottom-center, go clockwise
            r = 8  # corner radius
            left = cx - bw / 2
            right = cx + bw / 2
            top = cy + bh / 2
            bottom = cy - bh / 2

            # Rounded rectangle for body
            p.moveTo(left + r, bottom)
            p.lineTo(right - r, bottom)
            p.arcTo(right - 2 * r, bottom, right, bottom + 2 * r, -90, 90)
            p.lineTo(right, top - r)
            p.arcTo(right - 2 * r, top - 2 * r, right, top, 0, 90)
            p.lineTo(left + r, top)
            p.arcTo(left, top - 2 * r, left + 2 * r, top, 90, 90)
            p.lineTo(left, bottom + r)
            p.arcTo(left, bottom, left + 2 * r, bottom + 2 * r, 180, 90)
            p.close()

            c.setFillColor(colors.HexColor("#f5f5f5"))
            c.drawPath(p, fill=1, stroke=1)

            # Windshield (front - bottom of diagram = front of car)
            c.setLineWidth(0.5)
            ws_w = bw - 12
            c.rect(cx - ws_w / 2, bottom + 12, ws_w, 14, fill=0)
            c.setFont("Helvetica", 4)
            c.setFillColor(colors.black)
            c.drawCentredString(cx, bottom + 17, "PARA-BRISA")

            # Rear window (top of diagram = rear)
            c.rect(cx - ws_w / 2, top - 26, ws_w, 14, fill=0)
            c.drawCentredString(cx, top - 21, "VIDRO TRAS.")

            # Side windows
            sw_h = 25
            sw_w = 6
            # Left side windows
            c.rect(left + 1, cy - sw_h / 2, sw_w, sw_h, fill=0)
            # Right side windows
            c.rect(right - sw_w - 1, cy - sw_h / 2, sw_w, sw_h, fill=0)

            # Wheels (4 small black rectangles)
            c.setFillColor(colors.HexColor("#333333"))
            wh = 10
            ww = 5
            # Front left
            c.rect(left - ww + 1, bottom + 8, ww, wh, fill=1)
            # Front right
            c.rect(right - 1, bottom + 8, ww, wh, fill=1)
            # Rear left
            c.rect(left - ww + 1, top - 8 - wh, ww, wh, fill=1)
            # Rear right
            c.rect(right - 1, top - 8 - wh, ww, wh, fill=1)

            # Center line (hood to trunk)
            c.setStrokeColor(colors.HexColor("#cccccc"))
            c.setLineWidth(0.3)
            c.setDash(2, 2)
            c.line(cx, bottom + 28, cx, top - 28)
            c.setDash()

            # Labels
            c.setFont("Helvetica", 4)
            c.setFillColor(colors.black)
            c.drawCentredString(cx, bottom - 4, "FRENTE")
            c.drawCentredString(cx, top + 4, "TRASEIRA")
            c.drawString(left - 12, cy - 2, "ESQ")
            c.drawRightString(right + 14, cy - 2, "DIR")

            # Damage marking boxes around the car
            c.setStrokeColor(colors.HexColor("#999999"))
            c.setLineWidth(0.3)
            spots = [
                (left - 6, bottom + 2, "1"),
                (right + 2, bottom + 2, "2"),
                (left - 6, top - 8, "3"),
                (right + 2, top - 8, "4"),
                (cx - 3, bottom - 8, "5"),
                (cx - 3, top + 8, "6"),
            ]
            c.setFont("Helvetica", 4)
            for sx, sy, label in spots:
                c.rect(sx, sy, 6, 6, fill=0)
                c.drawCentredString(sx + 3, sy + 1.5, label)

            c.restoreState()
            return y - height

        # --- LEFT COLUMN: LOCATARIO ---
        y = y_line - 4
        y = draw_section_title(y, "LOCATARIO - RENTER")

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
        lx = margin
        lw = col_left_w
        fh = 18  # field height

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
        y = draw_section_title(y, "IDENTIFICACAO - IDENTIFICATION")
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
        y = draw_section_title(y, "CARRO - CAR")
        marca_tipo = "{} {}".format(veiculo.marca, veiculo.modelo) if veiculo else ""
        placa = veiculo.placa if veiculo else ""
        yt = y
        draw_field_box(lx, yt, "MARCA/TIPO:", marca_tipo, lw * 0.6, fh)
        y = draw_field_box(lx + lw * 0.6, yt, "PLACA:", placa, lw * 0.4, fh)

        # --- VISTORIA ---
        y -= 2
        y = draw_section_title(y, "VISTORIA VEICULO")

        # Fuel gauge
        c.setFont("Helvetica-Bold", 6)
        c.drawString(lx + 4, y - 10, "COMBUSTIVEL DE SAIDA")
        fuel_labels = ["RES.", "1/8", "1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "CHEIO"]
        fx = lx + 4
        fy = y - 22
        for i, fl in enumerate(fuel_labels):
            c.setFont("Helvetica", 5)
            c.drawString(fx + i * 28, fy, fl)
        c.line(lx + 4, fy - 3, lx + 4 + 28 * 9, fy - 3)
        fy -= 6
        for i, fl in enumerate(fuel_labels):
            c.drawString(fx + i * 28, fy, fl)
        y = fy - 12

        # Checklist items
        items = ["MACACO", "ESTEPE", "FERRAM.", "TRIANGULO", "DOCUMENTO", "EXTINTOR", "CALOTAS", "TOCA-FITAS", "CD PLAYER"]
        c.setFont("Helvetica", 6)
        for item in items:
            c.rect(lx + 4, y - 8, 8, 8)
            c.drawString(lx + 16, y - 7, item)
            y -= 11

        # Vehicle inspection diagram
        c.setFont("Helvetica-Bold", 7)
        c.drawString(lx + 4, y - 6, "Vehicle Inspection Diagram:")
        y = draw_car_inspection_diagram(lx + 4, y - 8, width=180, height=100)

        # Observacoes
        c.setFont("Helvetica-Bold", 6)
        obs_text = contrato.observacoes or ""
        c.drawString(lx + 4, y - 8, "Observacoes: {}".format(obs_text[:60]))
        y -= 30

        # === RIGHT COLUMN ===
        rx = w / 2 + 4
        rw = col_right_w
        ry = y_line - 4

        # --- QUILOMETRAGEM ---
        ry_sec = ry
        c.setFont("Helvetica-Bold", 9)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawCentredString(rx + rw / 2, ry_sec - 12, "QUILOMETRAGEM")
        ry_sec -= 20

        data_saida = contrato.data_inicio.strftime("%d/%m/%Y") if contrato.data_inicio else ""
        hora_saida = contrato.data_inicio.strftime("%H:%M") if contrato.data_inicio else ""
        data_entrada = contrato.data_fim.strftime("%d/%m/%Y") if contrato.data_fim else ""
        hora_entrada = contrato.data_fim.strftime("%H:%M") if contrato.data_fim else ""
        km_saida = "{:,.0f}".format(contrato.km_inicial) if contrato.km_inicial else ""
        km_entrada = "{:,.0f}".format(contrato.km_final) if contrato.km_final else ""

        # Quilometragem fields (2 columns)
        qh = 16
        hw2 = rw / 2
        fields_km = [
            ("DATA SAIDA:", data_saida, "DATA ENTRADA:", data_entrada),
            ("HORA SAIDA:", hora_saida, "HORA ENTRADA:", hora_entrada),
            ("KM SAIDA:", km_saida, "KM ENTRADA:", km_entrada),
            ("KM LIVRES/DIA:", "", "KM PERCORRIDOS:", ""),
        ]
        for f1l, f1v, f2l, f2v in fields_km:
            draw_field_box(rx, ry_sec, f1l, f1v, hw2, qh)
            ry_sec = draw_field_box(rx + hw2, ry_sec, f2l, f2v, hw2, qh)

        # --- QUILOMETRAGEM pricing table ---
        ry_sec -= 4
        c.setFont("Helvetica-Bold", 9)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawCentredString(rx + rw / 2, ry_sec - 12, "QUILOMETRAGEM")
        ry_sec -= 16

        # Table header
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
        dias = ""
        if contrato.data_inicio and contrato.data_fim:
            delta = contrato.data_fim - contrato.data_inicio
            dias = str(delta.days)

        rows = [
            ("DIARIA", dias, valor_diaria, valor_total),
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

        # TOTAL R$
        c.setFont("Helvetica-Bold", 7)
        c.rect(rx, ry_sec - 16, rw, 16)
        c.drawString(rx + rw * 0.5, ry_sec - 12, "TOTAL R$")
        c.drawString(rx + rw * 0.75, ry_sec - 12, valor_total)
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

        # --- Terms text ---
        c.setFont("Helvetica", 5.5)
        terms_lines = [
            "O cliente e responsavel por todas as infracoes de transito:",
            "autorizando a locadora debitar despesas extras em seu cartao de",
            "credito.",
            "Custumeris llable for all parking and traffic violations.",
            "Terminantemente proibido o trafego de carro em dunas e beira-mar,",
            "caso seja contatado incidira multa de R$ 1.000,00 (hum mil reais) e",
            "rescisao de contrato por parte da locadora.",
            "Depois de ter lido devidamente os termos e condicoes do contrato",
            "no anveso e verso, concordo expressamente, firmo presente.",
        ]
        for line in terms_lines:
            c.drawString(rx + 2, ry_sec, line)
            ry_sec -= 8

        # Assinatura do cliente
        ry_sec -= 6
        c.drawString(rx + 2, ry_sec, "___________________________________________________________")
        ry_sec -= 10
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(rx + rw / 2, ry_sec, "Assinatura do Cliente")
        ry_sec -= 14

        # --- TERMOS DE DECLARACAO DE MULTAS ---
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(rx + rw / 2, ry_sec, "TERMOS DE DECLARACAO DE MULTAS")
        ry_sec -= 12

        c.setFont("Helvetica", 5)
        multa_lines = [
            "Declaro conhecer a legislacao em vigor relativo ao novo Codigo",
            "de Transito Brasileiro e me responsabilizo inteiramente por quais quer",
            "penalidades decorrentes das infracoes por mim cometidas na",
            "conducao do veiculo locado, quer pecuniarias ou pontuacao, que",
            "serao informadas por MPCAR'S. A autoridade de transito, para que",
            "estas respectivas notificacoes e recibos de pagamento das multas,",
            "conforme verso e anverso deste contrato.",
            "",
            "O Locatario, desde ja constitui a LOCADORA sua bastante",
            "procuradora para fim especifico de atender resolucao no 72/98 do",
            "CONTRAN ficando a LOCADORA autorizada a assinar, em nome deste",
            "LOCATARIO e campo correspondente e assinatura do condutor",
            "infrator, no formulario de identificacao. Em caso de infracao de",
            "transito.",
            "",
            "Fica ainda estabelecido, que esta autorizacao so sera valida, se o",
        ]
        for line in multa_lines:
            c.drawString(rx + 2, ry_sec, line)
            ry_sec -= 7

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
        c.setFont("Helvetica", 6)

        # Two-column layout for terms
        col1_x = margin
        col2_x = w / 2 + 8
        col_w = w / 2 - margin - 8
        ty = h - margin

        clausulas_col1 = [
            "Carroceria, com hodometro instalado pelo fabricante,",
            "lacrado, em boas condicoes de utilizacao, encontra-se o",
            "veiculo locado;",
            "1) caracterizado no anverso deste documento, nos quadros",
            "respectivos, O(A) LOCATARIO(A) recebe e aceita com",
            "plenos conhecimentos o referido veiculo e respectivos",
            "acessorios, conforme relacao em anexo e se obriga a",
            "indenizar totalmente a LOCADORA no momento de entrega",
            "do veiculo, pelos acessorios eventualmente faltante, ao",
            "preco vigente no mercado.",
            "2) O preco de aluguel do veiculo locado sera declarado no",
            "anverso deste contrato calculado com base na tabela de",
            "tarifas da LOCADORA da qual o LOCATARIO (A) tem pleno",
            "conhecimento. Ficara ao(s) cargo(s) do(a) LOCATARIO(A)",
            "deste contrato; b) uma vez efetuada a devolucao do veiculo",
            "locado a LOCADORA, estabelecera o valor do aluguel, nos",
            "termos do presente contrato, precedendo ao desconto da",
            "quantia ja paga a titulo de adiantamento, devendo o(a)",
            "LOCATARIO(A) efetuar a LOCADORA o pagamento da",
            "diferenca resultante; c) por ocasiao da devolucao do",
            "veiculo, o(a) LOCATARIO(A) se compromete a pagar a",
            "LOCADORA O imposto sobre servicos incidentes sobre o",
            "custo total do aluguel e das tarifas adicionais; d) na falta de",
            "pagamento pontual dos servicos prestados ao",
            "LOCATARIO(A), ficara este(a) sujeito(a) ao pagamento de",
            "multa equivalente a 20% (vinte por cento) sobre o valor",
            "devido, acrescido de juros de 25% (vinte e cinco por cento)",
            "ao mes.",
            "3) O prazo de vigencia do presente contrato esta indicado no",
            "quadro respectivo, devendo o(a) LOCATARIO(A) efetuar a",
            "devolucao do veiculo no dia, hora e local estipulado, e",
            "somente podera ser prorrogado com anuencia da",
            "LOCADORA, por escrito no anverso do presente contrato.",
            "4) Findo o prazo contratual devera o(a)",
            "LOCATARIO(A)restituir o veiculo a LOCADORA, no mesmo",
            "estado em que recebeu, excluindo-se apenas o desgaste",
            "normal dos pneumaticos.",
            "5) A nao devolucao do veiculo locado por parte do(a)",
            "LOCATARIO(A), implicara na pratica de apropriacao",
            "indebita, ficando o(a) mesmo(a) sujeito(a) as leis penais,",
            "podendo a LOCADORA promover contra o(a)",
            "LOCATARIO(A) a competente representacao junto as",
            "autoridades policiais, para abertura de inquerito policial,",
            "bem como a retomada do veiculo locado.",
            "6) Todas e quaisquer despesas que se fizerem necessarias,",
            "para a retomada e posse do veiculo locado, inclusive",
            "judiciais e extrajudiciais, bem como aquelas decorrentes de",
            "transporte e remocao do mesmo. Correcao por conta",
            "exclusiva do(a) LOCATARIO(A).",
            "7) A LOCADORA podera propor contra o(a) LOCATARIO(A)",
            "as competentes acoes civeis que se fizerem necessarias.",
            "8) O veiculo locado destinar-se-a unico e exclusivo ao",
            "transporte de pessoas e a referido veiculo so podera ser",
            "conduzido pelo(a) LOCATARIO(A), ou, sob sua",
            "responsabilidade, pelo motorista ou motoristas por ele",
            "indicados, desde que estejam qualificados no anverso deste",
            "mesmo contrato.",
            "9) O(A) LOCATARIO(A) se obriga nao utilizar o veiculo",
            "locado em outro Estado sem o consentimento por da",
            "LOCADORA. 10) Sao obrigacoes do(a) LOCATARIO(A),",
            "bem como do(s) motoristas indicados pelo LOCATARIO.",
            "a) conduzir o veiculo locado durante a locacao, munido da",
            "documentacao legal correspondente, e expedida pelas",
            "autoridades competentes, que o autorizem a conduzir o",
            "veiculo locado;",
            "b) nao fazendo uso do veiculo para fins lucrativo;",
        ]

        for line in clausulas_col1:
            c.drawString(col1_x, ty, line)
            ty -= 8

        clausulas_col2 = [
            "c) nao sub-locar o veiculo;",
            "d) obedecer as leis de transito, Federal, Estadual e",
            "I) o pagamento das multas Impostas por quaisquer",
            "transgressoes a regulamentacao de transito ou qualquer",
            "outra regulamentacao (autorizando a locadora a debitar em",
            "cartao de credito); e ou emitir duplicata;",
            "m) responder por todos os atos licitos efetuados com veiculo",
            "no interior do mesmo;",
            "n) reembolsar a LOCADORA os correspondentes aos",
            "combustiveis faltante no caso do veiculo locado ser",
            "devolvido com menor quantidade de combustivel que havia",
            "no momento da entrega do veiculo a o(a) LOCATARIO(A).",
            "11) No caso de acidente ou desaparecimento do veiculo",
            "locado, durante o prazo de vigencia do presente contrato,",
            "o(a) LOCATARIO(A), se obriga a comunicar imediatamente",
            "o evento as AUTORIDADES competentes, apresentando o",
            "comprovante deste comunicado a LOCADORA, sob pena",
            "de ser responsabilizado(a) pelo abandono do veiculo, e:",
            "a) no caso de acidente ou qualquer outro incidente que",
            "venha a ser atribuido ao LOCATARIO(A), como",
            "consequencia do nao cumprimento das disposicoes",
            "contidas neste contrato o(a) LOCATARIO(A) reembolsara a",
            "LOCADORA o aluguel correspondente ao periodo em que,",
            "uma vez ultrapassado o prazo de locacao, o veiculo locado",
            "nao se encontre a disposicao da LOCADORA, bem como",
            "multa equivalente a 20% (vinte por sobre o valor devido,",
            "acrescido de juros de 25% (vinte e cinco por cento) ao mes.",
            "12) Se durante o prazo de locacao, ocorrer algum defeito no",
            "marcador de quilometragem (hodometro) o(a)",
            "LOCATARIO(A) se compromete a avisar de imediato a",
            "LOCADORA, para que se proceda ao conserto do referido",
            "defeito; neste caso fica, desde ja estabelecido entre as",
            "partes que a tarifa de quilometragem sera calculada com",
            "base na media de 1.000 (hum mil quilometros por dia).",
            "13) A LOCADORA nao se responsabiliza pelos objetos",
            "pessoais esquecidos pelo(a) LOCATARIO(A) ou seus",
            "passageiros no Interior do veiculo ou em seus",
            "estabelecimentos, nem pelos danos ou depreciacao",
            "sofrida por objetos transportados em seus veiculos.",
            "14) Este contrato se encerra:",
            "a) por haver expirado o prazo fixado no mesmo;",
            "b) por acordo expresso entre as partes;",
            "c) por rescisao;",
            "d) por perdas, danos ou defeitos desconhecidos que",
            "Inutilizem o veiculo aludido, ou pela destruicao do mesmo;",
            "e) por morte do(a) LOCATARIO(A).",
            "15) Dar-se-a a rescisao deste contrato, na hipotese do nao",
            "cumprimento por parte do(a) LOCATARIO(A) das",
            "obrigacoes pactuadas neste instrumento.",
        ]

        ry2 = h - margin
        for line in clausulas_col2:
            c.drawString(col2_x, ry2, line)
            ry2 -= 8

        # Signatures at bottom
        sig_y = min(ty, ry2) - 30
        if sig_y < 120:
            sig_y = 120

        c.setLineWidth(0.5)
        # Left signatures
        c.line(col1_x, sig_y, col1_x + 180, sig_y)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(col1_x, sig_y - 10, "LOCATARIO")

        c.line(col1_x, sig_y - 30, col1_x + 180, sig_y - 30)
        c.drawString(col1_x, sig_y - 40, "LOCADORA")

        # Right signatures
        c.line(col2_x, sig_y, col2_x + 180, sig_y)
        c.drawString(col2_x, sig_y - 10, "TESTEMUNHA 1")

        c.line(col2_x, sig_y - 30, col2_x + 180, sig_y - 30)
        c.drawString(col2_x, sig_y - 40, "TESTEMUNHA 2")

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
