import json
from typing import Tuple
import frontmatter


def parse_workflow_md(content: str) -> Tuple[dict, str]:
    """Parsea el contenido de un archivo Markdown con Frontmatter.

    Retorna una tupla: (frontmatter_dict, body_markdown)
    """
    post = frontmatter.loads(content)
    metadata = dict(post.metadata)
    body = post.content
    return metadata, body


def extract_metadata_fields(metadata: dict) -> dict:
    """Extrae campos conocidos del frontmatter y empaqueta el resto en JSON."""
    known_fields = {
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "engine": metadata.get("engine") or metadata.get("model"),
    }
    # Convertir todo el metadata a JSON por si existen otros campos dinámicos
    known_fields["raw_frontmatter_json"] = json.dumps(
        metadata, ensure_ascii=False
    )
    return known_fields