import re
from html.parser import HTMLParser


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div", "li", "h1", "h2", "h3", "tr"):
            self.parts.append("\n")


def html_a_texto(html: str) -> str:
    """Convierte HTML del editor enriquecido a texto plano para el LLM."""
    if not html:
        return ""
    if "<" not in html:
        return html
    stripper = _HTMLStripper()
    try:
        stripper.feed(html)
        texto = "".join(stripper.parts)
    except Exception:
        texto = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()