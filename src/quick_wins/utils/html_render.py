from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class EmailVariables(TypedDict):
    name: str
    unit_name: str
    sender_name: str


def render_template_html(template_path: Path, context: EmailVariables) -> str:
    html = Path(template_path).read_text(encoding="utf-8")
    for k, v in context.items():
        html = html.replace(f"{{{{{k}}}}}", str(v))
    return html
