from io import BytesIO

from docx import Document as DocxDocument


def parse_docx(content: bytes) -> str:
    document = DocxDocument(BytesIO(content))
    return "\n\n".join(
        paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()
    )
