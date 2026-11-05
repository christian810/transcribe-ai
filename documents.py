import io
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from docx import Document
from docx.shared import Pt, Cm, RGBColor


def clean(text):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)


def build_word(row, text):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(2.2)
    normal = doc.styles['Normal']
    normal.font.name = 'Calibri'
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(9)
    normal.paragraph_format.line_spacing = 1.15
    doc.add_heading('Transcripción', 0)
    doc.add_heading(clean(row['source']), 1)
    labels = {'auto': 'Automático', 'es': 'Castellano', 'ca': 'Catalán'}
    selected = labels.get(row['language'], row['language'])
    detected = labels.get(row['detected'], row['detected'] or 'Sin voz detectada')
    date = datetime.fromtimestamp(row['updated'], ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')
    for label, value in [('Fecha de procesamiento', date), ('Idioma seleccionado', selected), ('Idioma detectado', detected)]:
        p = doc.add_paragraph()
        p.add_run(label + ': ').bold = True
        p.add_run(value).font.color.rgb = RGBColor.from_string('475569')
    doc.add_paragraph()
    for paragraph in re.split(r'\n\s*\n', clean(text).strip()):
        doc.add_paragraph(paragraph)
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
