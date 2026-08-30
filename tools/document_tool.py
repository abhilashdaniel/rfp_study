"""
Document Tool
Extracts clean text from an uploaded supplier RFP PDF using PyMuPDF.
"""
import pymupdf


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts and lightly cleans text from a PDF given as raw bytes.
    Returns a single string with page breaks marked, suitable for prompting.
    """
    text_parts = []
    with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                text_parts.append(f"--- Page {page_num} ---\n{page_text}")

    full_text = "\n\n".join(text_parts)
    full_text = "\n".join(line.rstrip() for line in full_text.splitlines())
    return full_text.strip()
