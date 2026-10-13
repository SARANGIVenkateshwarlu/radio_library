#!/bin/sh
# Pipeline B: lesson Markdown -> print-ready A4 PDF with page footers.
# Usage: sh build_pdf.sh <lesson.md> <footer title> <final output.pdf>
set -e
MD="$1"; TITLE="$2"; OUT="$3"
BASE=$(basename "$MD" .md)
cd "$(dirname "$0")"

pandoc "$MD" -f markdown -t html5 -s --css=lesson_style.css -o "$BASE.html"
chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --disable-crashpad --user-data-dir=/tmp/chrome-prof --no-pdf-header-footer \
  --print-to-pdf="${BASE}_raw.pdf" "$BASE.html"

python3 - "$BASE" "$TITLE" "$OUT" <<'EOF'
import io, sys
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

base, title, out = sys.argv[1], sys.argv[2], sys.argv[3]
pdfmetrics.registerFont(TTFont("CJK", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"))
reader = PdfReader(f"{base}_raw.pdf")
writer = PdfWriter()
for i, page in enumerate(reader.pages, 1):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("CJK", 9)
    c.setFillGray(0.35)
    c.drawCentredString(A4[0] / 2, 24, f"{title} · 第 {i} 頁")
    c.save()
    buf.seek(0)
    page.merge_page(PdfReader(buf).pages[0])
    writer.add_page(page)
with open(out, "wb") as f:
    writer.write(f)
print(f"{out}: {len(reader.pages)} pages")
EOF
