"""Rebrand the distributed introduction, preserving pages and non-brand content.

Run with PyMuPDF 2.0 available on PYTHONPATH (authoring dependency only).
"""
from pathlib import Path
import pymupdf as pdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'reference/branding/originals/IN-DEPS_Product_Introduction_KR_v1.0.pdf'
OUTPUT = ROOT / 'frontend/help/IN-EDITAONE_Product_Introduction_KR_v1.0.pdf'
doc = pdf.open(SOURCE)
navy = (20 / 255, 35 / 255, 60 / 255)
for page in doc:
    changes = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                if 'IN-DEPS' not in span['text']:
                    continue
                color = tuple(((span['color'] >> shift) & 255) / 255 for shift in (16, 8, 0))
                for rect in page.search_for('IN-DEPS', clip=pdf.Rect(span['bbox'])):
                    # Use transparent redaction: the existing background is retained.
                    page.add_redact_annot(rect, fill=False)
                    changes.append((rect, span['size'], span['origin'][1], color))
    if page.number == 0:
        title_rect = pdf.Rect(45, 287, 490, 380)
        page.add_redact_annot(title_rect, fill=False)
    page.apply_redactions(images=0, graphics=0)
    for rect, size, baseline, color in changes:
        # Keep neighbouring Korean glyphs and line wrapping at their original positions.
        text = 'IN-EDITAONE'
        width = pdf.get_text_length(text, fontname='helv', fontsize=size)
        scale = rect.width / width
        origin = pdf.Point(rect.x0, baseline)
        page.insert_text(origin, text, fontname='helv', fontsize=size, color=color,
                         morph=(origin, pdf.Matrix(scale, 1)))
    if page.number == 0:
        page.insert_text((46.5, 326), 'IN-EDITAONE v1.0', fontname='hebo', fontsize=34, color=navy)
        page.insert_text((46.5, 358), 'INIT One-Stop Data Editing&Imputation Solution',
                         fontname='helv', fontsize=16, color=navy)
doc[0].replace_image(7, filename=str(ROOT / 'frontend/assets/ineditaone_banner_bilingual.png'))
metadata = doc.metadata
metadata.update(title='IN-EDITAONE Product Introduction v1.0', subject='INIT One-Stop Data Editing&Imputation Solution')
doc.set_metadata(metadata)
doc.save(OUTPUT, garbage=4, deflate=True)
doc.close()
with pdf.open(OUTPUT) as check:
    assert len(check) == 24
    assert all('IN-DEPS' not in p.get_text() for p in check)
    destination = ROOT / 'tmp/branding-qa/pdf'
    destination.mkdir(parents=True, exist_ok=True)
    for page in check:
        page.get_pixmap(matrix=pdf.Matrix(1, 1)).save(destination / f'page-{page.number + 1:02}.png')
print(f'Updated and rendered {OUTPUT.name}: 24 pages')
