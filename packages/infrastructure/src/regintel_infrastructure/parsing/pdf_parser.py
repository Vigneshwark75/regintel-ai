from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


def parse_pdf(content: bytes) -> list[ParsedPage]:
    reader = PdfReader(BytesIO(content))
    return [
        ParsedPage(page_number=index + 1, text=page.extract_text() or "")
        for index, page in enumerate(reader.pages)
    ]
