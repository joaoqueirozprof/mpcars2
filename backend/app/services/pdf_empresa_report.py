"""
PDF Consolidated Company Report — MPCARS layout (canvas-based).

Generates the empresa NF consolidada using the exact same visual style
as the rental contract PDF: ReportLab canvas, bordered sections with
blue headers, two-column field layout, and MPCARS header/footer.

Business logic is preserved from the original PDFNFService.
"""

from io import BytesIO
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors

from app.models import UsoVeiculoEmpresa, Empresa, Veiculo, DespesaNF


class PDFEmpresaReportService:
    """Generates consolidated empresa report with MPCARS contract layout."""

    # Page dimensions
    PAGE_WIDTH, PAGE_HEIGHT = A4
    MARGIN = 0.5 * cm

    # Colors — same as contract
    COLOR_HEADER_BG = colors.HexColor("#3B5998")
    COLOR_DARK_BG = colors.HexColor("#333333")
    COLOR_LIGHT_BG = colors.HexColor("#F0F0F0")
    COLOR_ALT_ROW = colors.HexColor("#F5F5F5")
    COLOR_TOTAL_BG = colors.HexColor("#E8F4F8")
    COLOR_BORDER = colors.HexColor("#CCCCCC")
    COLOR_SUCCESS = colors.HexColor("#27AE60")
    COLOR_DANGER = colors.HexColor("#E74C3C")
    COLOR_TEXT = colors.HexColor("#000000")
    COLOR_TEXT_LIGHT = colors.HexColor("#FFFFFF")
    COLOR_TEXT_MUTED = colors.HexColor("#666666")

    # Fonts
    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

    # Font sizes
    SIZE_TITLE = 18
    SIZE_SUBTITLE = 12
    SIZE_BLOCK_TITLE = 10
    SIZE_LABEL = 8
    SIZE_VALUE = 9
    SIZE_FOOTER = 7
    SIZE_TABLE_HEADER = 7
    SIZE_TABLE_CELL = 7

    # Column positions
    COL1_X = 0.5 * cm
    COL2_X = 10.5 * cm
    COL_WIDTH = 9.5 * cm
    FULL_WIDTH = 19.5 * cm

    # ================================================================
    # PUBLIC API
    # ================================================================

    @staticmethod
    def generate_nf_empresa_pdf(
        db,
        empresa_id: int,
        veiculos_km: List[dict],
    ) -> BytesIO:
        """
        Generate consolidated NF PDF for a company using contract layout.

        Args:
            db: SQLAlchemy session
            empresa_id: company ID
            veiculos_km: list of dicts {uso_id, km_percorrido, km_referencia?, valor_km_extra?}
        Returns:
            BytesIO buffer with the PDF
        """
        empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if not empresa:
            raise ValueError("Empresa nao encontrada")

        service = PDFEmpresaReportService()

        # --- Compute all vehicle rows ---
        rows = []
        totals = dict(
            km_percorrido=0.0,
            km_excedente=0.0,
            valor_extra=0.0,
            despesas=0.0,
            diarias=0.0,
            total=0.0,
        )

        for item in veiculos_km:
            uso_id = item.get("uso_id")
            km_input = item.get("km_percorrido", 0)
            km_ref_override = item.get("km_referencia")
            taxa_override = item.get("valor_km_extra")

            uso = db.query(UsoVeiculoEmpresa).filter(
                UsoVeiculoEmpresa.id == uso_id
            ).first()
            if not uso:
                continue

            veiculo = db.query(Veiculo).filter(Veiculo.id == uso.veiculo_id).first()
            despesas = db.query(DespesaNF).filter(DespesaNF.uso_id == uso_id).all()

            km_real = km_input or uso.km_percorrido or 0
            km_permitido = (
                km_ref_override
                if km_ref_override is not None
                else (uso.km_referencia or 0)
            )
            taxa = (
                taxa_override
                if taxa_override is not None
                else float(uso.valor_km_extra or 0)
            )
            km_exc = max(0, km_real - km_permitido)
            valor_exc = km_exc * taxa
            total_desp = sum(float(d.valor or 0) for d in despesas)

            valor_diaria = float(uso.valor_diaria_empresa or 0)
            subtotal = valor_diaria + valor_exc + total_desp

            totals["km_percorrido"] += km_real
            totals["km_excedente"] += km_exc
            totals["valor_extra"] += valor_exc
            totals["despesas"] += total_desp
            totals["diarias"] += valor_diaria
            totals["total"] += subtotal

            rows.append(dict(
                placa=veiculo.placa if veiculo else "N/A",
                modelo=f"{veiculo.marca or ''} {veiculo.modelo or ''}" if veiculo else "N/A",
                km_real=km_real,
                km_permitido=km_permitido,
                km_exc=km_exc,
                valor_exc=valor_exc,
                despesas=total_desp,
                valor_diaria=valor_diaria,
                subtotal=subtotal,
                data_inicio=uso.data_inicio,
                data_fim=uso.data_fim,
            ))

        # --- Build PDF ---
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        y = service.PAGE_HEIGHT - service.MARGIN

        # HEADER
        y = service._draw_header(c, y)

        # TITLE BAR
        y = service._draw_title_bar(c, y, "RELATÓRIO CONSOLIDADO DE USO DE VEÍCULOS - EMPRESA")

        # EMPRESA DATA (left column)
        y_section = y - 0.4 * cm
        y_section = service._draw_empresa_block(c, y_section, empresa)

        # RESUMO FINANCEIRO (right side, same height as empresa block)
        service._draw_resumo_lateral(c, y - 0.4 * cm, totals)

        y = y_section - 0.3 * cm

        # VEÍCULOS TABLE
        y = service._draw_veiculos_table(c, y, rows, totals)

        # TOTAL GERAL BOX
        y = service._draw_total_geral(c, y, totals)

        # FOOTER
        service._draw_footer(c)

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

    # ================================================================
    # DRAWING METHODS
    # ================================================================

    def _draw_header(self, c, y):
        """Draw MPCARS header — identical to contract."""
        # Company name
        c.setFont(self.FONT_BOLD, 22)
        c.setFillColor(self.COLOR_HEADER_BG)
        c.drawString(self.COL1_X + 0.2 * cm, y - 0.8 * cm, "MPCARS")

        c.setFont(self.FONT_REGULAR, 8)
        c.setFillColor(self.COLOR_TEXT_MUTED)
        c.drawString(self.COL1_X + 0.2 * cm, y - 1.2 * cm, "VEÍCULOS E LOCAÇÕES")

        # Right-aligned title
        c.setFont(self.FONT_BOLD, 16)
        c.setFillColor(self.COLOR_TEXT)
        c.drawRightString(
            self.PAGE_WIDTH - self.MARGIN - 0.2 * cm,
            y - 0.8 * cm,
            "RELATÓRIO DE EMPRESA",
        )

        # Company details
        c.setFont(self.FONT_REGULAR, self.SIZE_FOOTER)
        c.setFillColor(self.COLOR_TEXT_MUTED)
        c.drawString(
            self.COL1_X + 0.2 * cm,
            y - 1.7 * cm,
            "CNPJ: 52.471.526/0001-53    Tel: (84) 99911-0504",
        )
        c.drawString(
            self.COL1_X + 0.2 * cm,
            y - 2.1 * cm,
            "RUA MANOEL ALEXANDRE 1048 - LJ 02 - EDIFÍCIO COMERCIAL E RESIDENCIAL",
        )
        c.drawString(
            self.COL1_X + 0.2 * cm,
            y - 2.4 * cm,
            "PRINCESINHA DO OESTE - CEP 59900-000 - PAU DOS FERROS-RN",
        )

        # Separator line
        c.setStrokeColor(self.COLOR_BORDER)
        c.setLineWidth(0.5)
        c.line(
            self.COL1_X, y - 2.7 * cm,
            self.PAGE_WIDTH - self.MARGIN, y - 2.7 * cm,
        )

        c.setFillColor(self.COLOR_TEXT)
        return y - 3.0 * cm

    def _draw_title_bar(self, c, y, title):
        """Draw a full-width colored title bar."""
        bar_height = 0.6 * cm
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(self.COL1_X, y - bar_height, self.FULL_WIDTH, bar_height, fill=1)

        c.setFont(self.FONT_BOLD, 11)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawCentredString(self.PAGE_WIDTH / 2, y - bar_height + 0.18 * cm, title)

        c.setFillColor(self.COLOR_TEXT)
        return y - bar_height - 0.15 * cm

    def _draw_empresa_block(self, c, y, empresa):
        """Draw EMPRESA LOCATÁRIA section (left column)."""
        y = self._draw_block_title(c, y, "EMPRESA LOCATÁRIA", self.COL1_X)

        fields = [
            ("RAZÃO SOCIAL", empresa.razao_social or empresa.nome or "N/A"),
            ("CNPJ", empresa.cnpj or "N/A"),
            ("ENDEREÇO", empresa.endereco or "N/A"),
            ("CIDADE/UF", f"{empresa.cidade or ''} - {empresa.estado or ''}"),
            ("CEP", empresa.cep or ""),
            ("CONTATO", empresa.contato_principal or "N/A"),
            ("TELEFONE", empresa.telefone or "N/A"),
            ("E-MAIL", empresa.email or "N/A"),
        ]

        row_height = 0.45 * cm
        for i, (label, value) in enumerate(fields):
            y_pos = y - i * row_height

            # Alternate row background
            if i % 2 == 0:
                c.setFillColor(self.COLOR_ALT_ROW)
                c.rect(
                    self.COL1_X, y_pos - row_height,
                    self.COL_WIDTH, row_height, fill=1, stroke=0,
                )

            # Border
            c.setStrokeColor(self.COLOR_BORDER)
            c.setLineWidth(0.3)
            c.rect(
                self.COL1_X, y_pos - row_height,
                self.COL_WIDTH, row_height, fill=0, stroke=1,
            )

            # Label
            c.setFillColor(self.COLOR_TEXT)
            c.setFont(self.FONT_BOLD, self.SIZE_LABEL)
            c.drawString(self.COL1_X + 0.2 * cm, y_pos - 0.32 * cm, f"{label}:")

            # Value
            c.setFont(self.FONT_REGULAR, self.SIZE_VALUE)
            c.drawString(self.COL1_X + 3.5 * cm, y_pos - 0.32 * cm, str(value))

        return y - len(fields) * row_height

    def _draw_resumo_lateral(self, c, y, totals):
        """Draw RESUMO FINANCEIRO on the right column."""
        y = self._draw_block_title(c, y, "RESUMO FINANCEIRO", self.COL2_X)

        items = [
            ("VALOR BASE (DIÁRIAS)", self._fmt_currency(totals["diarias"])),
            ("KM EXCEDENTE", f'{totals["km_excedente"]:,.1f} km'),
            ("VALOR KM EXCEDENTE", self._fmt_currency(totals["valor_extra"])),
            ("TOTAL DESPESAS", self._fmt_currency(totals["despesas"])),
        ]

        row_height = 0.45 * cm
        for i, (label, value) in enumerate(items):
            y_pos = y - i * row_height

            if i % 2 == 0:
                c.setFillColor(self.COLOR_ALT_ROW)
                c.rect(
                    self.COL2_X, y_pos - row_height,
                    self.COL_WIDTH, row_height, fill=1, stroke=0,
                )

            c.setStrokeColor(self.COLOR_BORDER)
            c.setLineWidth(0.3)
            c.rect(
                self.COL2_X, y_pos - row_height,
                self.COL_WIDTH, row_height, fill=0, stroke=1,
            )

            c.setFillColor(self.COLOR_TEXT)
            c.setFont(self.FONT_BOLD, self.SIZE_LABEL)
            c.drawString(self.COL2_X + 0.2 * cm, y_pos - 0.32 * cm, f"{label}:")

            c.setFont(self.FONT_REGULAR, self.SIZE_VALUE)
            c.drawRightString(
                self.COL2_X + self.COL_WIDTH - 0.3 * cm,
                y_pos - 0.32 * cm,
                str(value),
            )

        # TOTAL GERAL row (highlighted)
        y_total = y - len(items) * row_height
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(
            self.COL2_X, y_total - row_height,
            self.COL_WIDTH, row_height, fill=1, stroke=0,
        )
        c.setFont(self.FONT_BOLD, self.SIZE_BLOCK_TITLE)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawString(self.COL2_X + 0.2 * cm, y_total - 0.33 * cm, "TOTAL GERAL:")
        c.drawRightString(
            self.COL2_X + self.COL_WIDTH - 0.3 * cm,
            y_total - 0.33 * cm,
            self._fmt_currency(totals["total"]),
        )
        c.setFillColor(self.COLOR_TEXT)

    def _draw_veiculos_table(self, c, y, rows, totals):
        """Draw the vehicles table spanning full width."""
        y -= 0.3 * cm
        y = self._draw_block_title_full(c, y, "RESUMO POR VEÍCULO")

        # Column definitions: (header, width, align)
        col_defs = [
            ("PLACA", 2.2 * cm, "left"),
            ("MODELO", 3.2 * cm, "left"),
            ("KM PERCORR.", 2.2 * cm, "right"),
            ("KM PERMIT.", 2.2 * cm, "right"),
            ("KM EXCED.", 2.0 * cm, "right"),
            ("VLR EXTRA", 2.2 * cm, "right"),
            ("DESPESAS", 2.2 * cm, "right"),
            ("TOTAL", 2.8 * cm, "right"),
        ]

        table_x = self.COL1_X
        row_height = 0.4 * cm

        # --- Header row ---
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=1, stroke=0)

        c.setFont(self.FONT_BOLD, self.SIZE_TABLE_HEADER)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        x = table_x
        for header, width, align in col_defs:
            if align == "right":
                c.drawRightString(x + width - 0.15 * cm, y - 0.28 * cm, header)
            else:
                c.drawString(x + 0.15 * cm, y - 0.28 * cm, header)
            x += width

        y -= row_height
        c.setFillColor(self.COLOR_TEXT)

        # --- Data rows ---
        for idx, row in enumerate(rows):
            # Check if we need a new page
            if y - row_height < 3.5 * cm:
                self._draw_footer(c)
                c.showPage()
                y = self.PAGE_HEIGHT - self.MARGIN - 0.5 * cm
                # Redraw table header on new page
                c.setFillColor(self.COLOR_HEADER_BG)
                c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=1, stroke=0)
                c.setFont(self.FONT_BOLD, self.SIZE_TABLE_HEADER)
                c.setFillColor(self.COLOR_TEXT_LIGHT)
                x = table_x
                for header, width, align in col_defs:
                    if align == "right":
                        c.drawRightString(x + width - 0.15 * cm, y - 0.28 * cm, header)
                    else:
                        c.drawString(x + 0.15 * cm, y - 0.28 * cm, header)
                    x += width
                y -= row_height
                c.setFillColor(self.COLOR_TEXT)

            # Alternate background
            if idx % 2 == 0:
                c.setFillColor(self.COLOR_ALT_ROW)
                c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=1, stroke=0)

            # Row border
            c.setStrokeColor(self.COLOR_BORDER)
            c.setLineWidth(0.3)
            c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=0, stroke=1)

            # Cell values
            values = [
                row["placa"],
                row["modelo"][:22],
                f'{row["km_real"]:,.1f}',
                f'{row["km_permitido"]:,.1f}',
                f'{row["km_exc"]:,.1f}',
                self._fmt_currency(row["valor_exc"]),
                self._fmt_currency(row["despesas"]),
                self._fmt_currency(row["subtotal"]),
            ]

            c.setFont(self.FONT_REGULAR, self.SIZE_TABLE_CELL)
            c.setFillColor(self.COLOR_TEXT)
            x = table_x
            for i, (_, width, align) in enumerate(col_defs):
                val = values[i]
                # Highlight KM excedente in red if > 0
                if i == 4 and row["km_exc"] > 0:
                    c.setFillColor(self.COLOR_DANGER)
                    c.setFont(self.FONT_BOLD, self.SIZE_TABLE_CELL)

                if align == "right":
                    c.drawRightString(x + width - 0.15 * cm, y - 0.28 * cm, val)
                else:
                    c.drawString(x + 0.15 * cm, y - 0.28 * cm, val)

                # Reset color
                if i == 4 and row["km_exc"] > 0:
                    c.setFillColor(self.COLOR_TEXT)
                    c.setFont(self.FONT_REGULAR, self.SIZE_TABLE_CELL)

                x += width

            y -= row_height

        # --- Totals row ---
        c.setFillColor(self.COLOR_TOTAL_BG)
        c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=1, stroke=0)
        c.setStrokeColor(self.COLOR_BORDER)
        c.rect(table_x, y - row_height, self.FULL_WIDTH, row_height, fill=0, stroke=1)

        total_values = [
            "TOTAL",
            f"{len(rows)} veíc.",
            f'{totals["km_percorrido"]:,.1f}',
            "",
            f'{totals["km_excedente"]:,.1f}',
            self._fmt_currency(totals["valor_extra"]),
            self._fmt_currency(totals["despesas"]),
            self._fmt_currency(totals["total"]),
        ]

        c.setFont(self.FONT_BOLD, self.SIZE_TABLE_CELL)
        c.setFillColor(self.COLOR_TEXT)
        x = table_x
        for i, (_, width, align) in enumerate(col_defs):
            val = total_values[i]
            if align == "right":
                c.drawRightString(x + width - 0.15 * cm, y - 0.28 * cm, val)
            else:
                c.drawString(x + 0.15 * cm, y - 0.28 * cm, val)
            x += width

        y -= row_height

        return y

    def _draw_total_geral(self, c, y, totals):
        """Draw the TOTAL GERAL A PAGAR box."""
        y -= 0.4 * cm
        box_height = 0.7 * cm

        # Dark blue bar
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(self.COL1_X, y - box_height, self.FULL_WIDTH, box_height, fill=1, stroke=0)

        c.setFont(self.FONT_BOLD, 14)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawString(self.COL1_X + 0.4 * cm, y - 0.48 * cm, "TOTAL GERAL A PAGAR:")
        c.drawRightString(
            self.COL1_X + self.FULL_WIDTH - 0.4 * cm,
            y - 0.48 * cm,
            self._fmt_currency(totals["total"]),
        )

        c.setFillColor(self.COLOR_TEXT)
        return y - box_height - 0.3 * cm

    def _draw_footer(self, c):
        """Draw page footer — same style as contract."""
        footer_y = self.MARGIN + 0.3 * cm

        # Bottom bar
        c.setFillColor(self.COLOR_DARK_BG)
        c.rect(0, 0, self.PAGE_WIDTH, self.MARGIN + 0.8 * cm, fill=1, stroke=0)

        c.setFont(self.FONT_REGULAR, self.SIZE_FOOTER)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawCentredString(
            self.PAGE_WIDTH / 2,
            footer_y + 0.25 * cm,
            "RUA MANOEL ALEXANDRE 1048 - LJ 02 - EDIFÍCIO COMERCIAL E RESIDENCIAL",
        )
        c.drawCentredString(
            self.PAGE_WIDTH / 2,
            footer_y,
            "PRINCESINHA DO OESTE - CEP 59900-000 - PAU DOS FERROS-RN",
        )
        c.drawCentredString(
            self.PAGE_WIDTH / 2,
            footer_y - 0.25 * cm,
            f"CNPJ: 52.471.526/0001-53    (84) 99911-0504    |    Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
        )

        c.setFillColor(self.COLOR_TEXT)

    # ================================================================
    # HELPER METHODS
    # ================================================================

    def _draw_block_title(self, c, y, title, x_pos):
        """Draw a section title bar (column width)."""
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(x_pos, y - 0.4 * cm, self.COL_WIDTH, 0.4 * cm, fill=1, stroke=0)

        c.setFont(self.FONT_BOLD, self.SIZE_BLOCK_TITLE)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawString(x_pos + 0.15 * cm, y - 0.32 * cm, title)

        c.setFillColor(self.COLOR_TEXT)
        return y - 0.55 * cm

    def _draw_block_title_full(self, c, y, title):
        """Draw a section title bar (full width)."""
        c.setFillColor(self.COLOR_HEADER_BG)
        c.rect(self.COL1_X, y - 0.4 * cm, self.FULL_WIDTH, 0.4 * cm, fill=1, stroke=0)

        c.setFont(self.FONT_BOLD, self.SIZE_BLOCK_TITLE)
        c.setFillColor(self.COLOR_TEXT_LIGHT)
        c.drawString(self.COL1_X + 0.15 * cm, y - 0.32 * cm, title)

        c.setFillColor(self.COLOR_TEXT)
        return y - 0.55 * cm

    @staticmethod
    def _fmt_currency(value) -> str:
        """Format as R$ X.XXX,XX"""
        try:
            v = float(value or 0)
            return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "R$ 0,00"

    @staticmethod
    def _fmt_date(d) -> str:
        if not d:
            return "N/A"
        if isinstance(d, (datetime, date)):
            return d.strftime("%d/%m/%Y")
        return str(d)
