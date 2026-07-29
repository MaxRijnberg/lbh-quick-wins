from __future__ import annotations

from pathlib import Path


def render_template_html(template_path: Path, context: dict) -> str:
    html = Path(template_path).read_text(encoding="utf-8")
    for k, v in context.items():
        html = html.replace(f"{{{{{k}}}}}", str(v))
    return html
