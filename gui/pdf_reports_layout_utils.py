"""ReportLab layout helpers kept separate from report orchestration."""

from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

from gui.pdf_reports_utils import event_date, event_time_range


def draw_header_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#1caae2"))
    canvas.setLineWidth(1)
    canvas.line(20 * mm, 18 * mm, A4[0] - 20 * mm, 18 * mm)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 12 * mm, "Rapport généré par Fuel Theft Detector")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_table(data, widths, header_rows=1):
    table = Table(data, colWidths=widths, repeatRows=header_rows, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1caae2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.7, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def report_styles():
    styles = getSampleStyleSheet()
    return (
        ParagraphStyle("ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                       fontSize=21, leading=26, alignment=TA_LEFT, spaceAfter=12),
        ParagraphStyle("ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
                       fontSize=14, leading=18, spaceBefore=4, spaceAfter=10),
        ParagraphStyle("ReportBody", parent=styles["BodyText"], fontSize=10, leading=14),
    )


def cover_story(site, period, title_style, heading_style, body_style):
    return [
        Spacer(1, 28 * mm),
        Table([[Paragraph("RAPPORT VOL FUEL", title_style)]], colWidths=[170 * mm], style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ])),
        Spacer(1, 12 * mm),
        Paragraph(f"<b>SITE :</b> {escape(site)}", title_style),
        Paragraph(f"<b>PERIODE :</b> {period}", title_style),
        Spacer(1, 70 * mm),
        Paragraph(f"Date de création : {datetime.now():%d/%m/%Y}", body_style),
        Paragraph("Auteur : Fuel Theft Detector", body_style),
        PageBreak(),
        Paragraph("1. Récapitulatif", heading_style),
    ]


def summary_rows(events):
    rows = [["Date", "Tranche horaire", "Quantité"]]
    total = 0.0
    for event in events:
        quantity = float(event.get("fuel_drop") or 0)
        total += quantity
        rows.append([event_date(event), event_time_range(event), f"{quantity:g} L"])
    rows.append(["", "Total", f"{total:g} L"])
    return rows, total
