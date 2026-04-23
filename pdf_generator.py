import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.platypus import Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

KATEGORIE_NAMES = {
    "A": "Motorrad", "B": "Auto", "C": "LKW",
    "D": "Bus", "E": "Boot", "F": "Flugzeug"
}

LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")


def build_pdf(pruefung: dict, output_path: str) -> str:
    """Erstellt ein PDF-Zeugnis für eine bestandene praktische Prüfung."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    style_subtitle = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=13,
        textColor=colors.HexColor("#16213e"),
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName="Helvetica",
    )
    style_school = ParagraphStyle(
        "School",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#0f3460"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    style_label = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#555555"),
        fontName="Helvetica",
    )
    style_value = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
    )
    style_footer = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    style_passed = ParagraphStyle(
        "Passed",
        parent=styles["Normal"],
        fontSize=16,
        textColor=colors.HexColor("#27ae60"),
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )

    elements = []

    # Logo
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=45 * mm, height=45 * mm)
            logo.hAlign = "CENTER"
            elements.append(logo)
            elements.append(Spacer(1, 4 * mm))
        except Exception as e:
            logger.warning(f"Logo konnte nicht geladen werden: {e}")

    # Kopfzeile
    elements.append(Paragraph("Washington Driving School", style_school))
    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph("Prüfungszeugnis", style_title))
    elements.append(Paragraph("Praktische Fahrprüfung", style_subtitle))
    elements.append(Spacer(1, 5 * mm))

    # Bestanden-Banner
    kat = pruefung.get("kategorie", "B").upper()
    kat_name = KATEGORIE_NAMES.get(kat, kat)
    elements.append(Paragraph(f"✓  BESTANDEN  –  Kategorie {kat} ({kat_name})", style_passed))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#27ae60")))
    elements.append(Spacer(1, 8 * mm))

    # Kandidaten-Daten Tabelle
    datum_str = pruefung.get("datum", datetime.now().strftime("%d.%m.%Y"))

    data = [
        [Paragraph("VORNAME", style_label), Paragraph(pruefung.get("vorname", ""), style_value),
         Paragraph("NACHNAME", style_label), Paragraph(pruefung.get("nachname", ""), style_value)],
        [Paragraph("GEBURTSDATUM", style_label), Paragraph(pruefung.get("geburtsdatum", ""), style_value),
         Paragraph("TELEFON", style_label), Paragraph(pruefung.get("telefon", ""), style_value)],
        [Paragraph("PSN", style_label), Paragraph(pruefung.get("psn", ""), style_value),
         Paragraph("KATEGORIE", style_label), Paragraph(f"{kat} – {kat_name}", style_value)],
        [Paragraph("PRÜFUNGSDATUM", style_label), Paragraph(datum_str, style_value),
         Paragraph("", style_label), Paragraph("", style_value)],
    ]

    col_w = [35 * mm, 60 * mm, 35 * mm, 60 * mm]
    table = Table(data, colWidths=col_w)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8f9fa"), colors.HexColor("#eef0f2")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10 * mm))

    # Fahrlehrer-Abschnitt
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    elements.append(Spacer(1, 4 * mm))

    fl_data = [
        [Paragraph("FAHRLEHRER", style_label), Paragraph(pruefung.get("fahrlehrer_name", ""), style_value)],
        [Paragraph("UNTERSCHRIFT", style_label), Paragraph(pruefung.get("unterschrift", ""), style_value)],
    ]
    if pruefung.get("bemerkung"):
        fl_data.append([
            Paragraph("BEMERKUNG", style_label),
            Paragraph(pruefung.get("bemerkung", ""), style_value),
        ])

    fl_table = Table(fl_data, colWidths=[35 * mm, 145 * mm])
    fl_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(fl_table)
    elements.append(Spacer(1, 15 * mm))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e")))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        f"Washington Driving School  •  Ausgestellt am {datum_str}  •  Dieses Dokument ist offiziell.",
        style_footer
    ))

    doc.build(elements)
    logger.info(f"PDF erstellt: {output_path}")
    return output_path
