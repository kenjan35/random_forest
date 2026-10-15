import os
import re
import tempfile
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


MONTHS_FR = (
    "JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
    "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE",
)


def _safe_filename(value):
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_")
    return normalized or "SITE"


def _period_label(start_date):
    try:
        parsed = datetime.strptime(start_date, "%Y-%m-%d")
        return f"{MONTHS_FR[parsed.month - 1]} {parsed.year}"
    except (TypeError, ValueError):
        return str(start_date or "PERIODE").upper()


def _parse_timestamp(value):
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_date(event):
    value = str(event.get("ts_start", ""))
    parsed = _parse_timestamp(value)
    return parsed.strftime("%d/%m/%Y") if parsed else value[:10]


def _event_time(value):
    """HH:MM, quel que soit le format (secondes, millisecondes, fuseau 'Z'...)."""
    parsed = _parse_timestamp(value)
    return parsed.strftime("%H:%M") if parsed else str(value)[-8:-3]


def _event_time_range(event):
    return f"{_event_time(event.get('ts_start', ''))} - {_event_time(event.get('ts_end', ''))}"


def _draw_header_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#1caae2"))
    canvas.setLineWidth(1)
    canvas.line(20 * mm, 18 * mm, A4[0] - 20 * mm, 18 * mm)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20 * mm, 12 * mm, "Rapport généré par Fuel Theft Detector")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


def _build_table(data, widths, header_rows=1):
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


def create_site_report(result, output_path, period_start, period_end, chart_saver):
    events = list(result.get("events", []))
    if not events:
        raise ValueError("Ce site ne contient aucun vol détecté.")

    site = str(result.get("site") or result.get("filename") or "Site")
    site_markup = escape(site)  # "&", "<" dans un nom de site cassent le rendu reportlab
    period = _period_label(period_start)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=21, leading=26, alignment=TA_LEFT, spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "ReportHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, spaceBefore=4, spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontSize=10, leading=14,
    )

    document = SimpleDocTemplate(
        output_path, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=25 * mm,
        title=f"RAPPORT VOL FUEL - {site}", author="Fuel Theft Detector",
    )
    story = [
        Spacer(1, 28 * mm),
        Table([[Paragraph("RAPPORT VOL FUEL", title_style)]], colWidths=[170 * mm], style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ])),
        Spacer(1, 12 * mm),
        Paragraph(f"<b>SITE :</b> {site_markup}", title_style),
        Paragraph(f"<b>PERIODE :</b> {period}", title_style),
        Spacer(1, 70 * mm),
        Paragraph(f"Date de création : {datetime.now():%d/%m/%Y}", body_style),
        Paragraph("Auteur : Fuel Theft Detector", body_style),
        PageBreak(),
        Paragraph("1. Récapitulatif", heading_style),
    ]

    summary_rows = [["Date", "Tranche horaire", "Quantité"]]
    total = 0.0
    for event in events:
        quantity = float(event.get("fuel_drop") or 0)
        total += quantity
        summary_rows.append([_event_date(event), _event_time_range(event), f"{quantity:g} L"])
    summary_rows.append(["", "Total", f"{total:g} L"])
    story.append(_build_table(summary_rows, [42 * mm, 62 * mm, 35 * mm]))
    story.extend([Spacer(1, 18 * mm), PageBreak(), Paragraph(f"2. {period}", heading_style)])

    detail_rows = [["Date", "Tranche horaire", "Quantité", "Capture d'écran"]]
    temporary_images = []
    try:
        for event in events:
            # mktemp() est obsolète (nom réservé sans fichier créé) : on crée le fichier
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                image_path = handle.name
            temporary_images.append(image_path)
            chart_saver(result, image_path, event)
            image = Image(image_path, width=78 * mm, height=43 * mm)
            image.hAlign = "CENTER"
            detail_rows.append([
                _event_date(event), _event_time_range(event),
                f"{float(event.get('fuel_drop') or 0):g} L", image,
            ])
        detail_rows.append(["", "Total", f"{total:g} L", ""])
        detail = _build_table(detail_rows, [27 * mm, 29 * mm, 20 * mm, 94 * mm])
        story.append(detail)
        document.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    finally:
        for image_path in temporary_images:
            if os.path.exists(image_path):
                os.remove(image_path)


def create_reports(results, output_dir, period_start, period_end, chart_saver):
    os.makedirs(output_dir, exist_ok=True)
    period = _period_label(period_start)
    paths = []
    for result in results:
        if result.get("error") or not result.get("has_theft"):
            continue
        site = _safe_filename(result.get("site") or result.get("filename"))
        path = os.path.join(output_dir, f"RAPPORT_VOL_FUEL_{site}_{_safe_filename(period)}.pdf")
        create_site_report(result, path, period_start, period_end, chart_saver)
        paths.append(path)
    return paths
