import os
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from gui.pdf_reports_utils import (
    event_date as _event_date,
    event_time_range as _event_time_range,
    period_label as _period_label,
    safe_filename as _safe_filename,
)
from gui.pdf_reports_layout_utils import (
    build_table as _build_table,
    cover_story as _cover_story,
    draw_header_footer as _draw_header_footer,
    report_styles as _report_styles,
    summary_rows as _summary_rows,
)

def _detail_rows(result, events, chart_saver):
    rows = [["Date", "Tranche horaire", "Quantité", "Capture d'écran"]]
    images = []
    for event in events:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            image_path = handle.name
        images.append(image_path)
        chart_saver(result, image_path, event)
        image = Image(image_path, width=78 * mm, height=43 * mm)
        image.hAlign = "CENTER"
        rows.append([_event_date(event), _event_time_range(event),
                     f"{float(event.get('fuel_drop') or 0):g} L", image])
    return rows, images


def _remove_files(paths):
    for path in paths:
        if os.path.exists(path):
            os.remove(path)


def create_site_report(result, output_path, period_start, chart_saver):
    events = list(result.get("events", []))
    if not events:
        raise ValueError("Ce site ne contient aucun vol détecté.")

    site = str(result.get("site") or result.get("filename") or "Site")
    period = _period_label(period_start)
    title_style, heading_style, body_style = _report_styles()

    document = SimpleDocTemplate(
        output_path, pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=25 * mm,
        title=f"RAPPORT VOL FUEL - {site}", author="Fuel Theft Detector",
    )
    story = _cover_story(site, period, title_style, heading_style, body_style)
    summary_rows, total = _summary_rows(events)
    story.append(_build_table(summary_rows, [42 * mm, 62 * mm, 35 * mm]))
    story.extend([Spacer(1, 18 * mm), PageBreak(), Paragraph(f"2. {period}", heading_style)])
    temporary_images = []
    try:
        detail_rows, temporary_images = _detail_rows(result, events, chart_saver)
        detail_rows.append(["", "Total", f"{total:g} L", ""])
        detail = _build_table(detail_rows, [27 * mm, 29 * mm, 20 * mm, 94 * mm])
        story.append(detail)
        document.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    finally:
        _remove_files(temporary_images)


def create_reports(results, output_dir, period_start, _period_end, chart_saver):
    os.makedirs(output_dir, exist_ok=True)
    period = _period_label(period_start)
    paths = []
    for result in results:
        if result.get("error") or not result.get("has_theft"):
            continue
        site = _safe_filename(result.get("site") or result.get("filename"))
        path = os.path.join(output_dir, f"RAPPORT_VOL_FUEL_{site}_{_safe_filename(period)}.pdf")
        create_site_report(result, path, period_start, chart_saver)
        paths.append(path)
    return paths
