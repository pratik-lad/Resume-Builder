"""OCR is the fallback, never the default.

Rule: only fires when the extracted text is degenerate (see ParsedDoc.is_degenerate).
OCR is slow (1-4 s/page) and noisy; it rescues ~5% of inputs and degrades them.
"""
import logging

from parsers.pdf_parser import Line, ParsedDoc

log = logging.getLogger(__name__)


def ocr_pdf(path: str, dpi: int = 300) -> ParsedDoc:
    try:
        import fitz
        from rapidocr_onnxruntime import RapidOCR  # optional dependency
    except ImportError:
        log.warning("OCR requested but rapidocr-onnxruntime is not installed")
        return ParsedDoc(warnings=["OCR unavailable: pip install rapidocr-onnxruntime"])

    engine = RapidOCR()
    doc = fitz.open(path)
    lines: list[Line] = []
    cursor = 0

    for pno, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        result, _ = engine(pix.tobytes("png"))
        for item in result or []:
            text = str(item[1]).strip()
            if not text:
                continue
            ln = Line(text=text, page=pno, x0=0.0, y0=float(cursor), size=10.0, bold=False)
            ln.char_start = cursor
            ln.char_end = cursor + len(text)
            cursor = ln.char_end + 1
            lines.append(ln)

    raw = "\n".join(l.text for l in lines)
    return ParsedDoc(lines=lines, raw_text=raw, warnings=["text recovered via OCR"])
