import json
from typing import Any, Dict, Tuple
import frontmatter


def parse_workflow_md(content: str) -> Tuple[dict, str]:
    """Parsea el contenido de un archivo Markdown con Frontmatter.

    Garantiza que todas las claves del diccionario de metadatos sean cadenas de texto (str).
    """
    post = frontmatter.loads(content)

    # Convertir todas las claves del frontmatter a str para evitar 'keywords must be strings'
    clean_metadata: Dict[str, Any] = {}
    if isinstance(post.metadata, dict):
        for k, v in post.metadata.items():
            clean_metadata[str(k)] = v

    body = post.content
    return clean_metadata, body


def extract_metadata_fields(metadata: dict) -> dict:
    """Extrae campos conocidos del frontmatter y empaqueta el resto en JSON."""
    known_fields = {
        "title": str(metadata.get("title"))
        if metadata.get("title") is not None
        else None,
        "description": str(metadata.get("description"))
        if metadata.get("description") is not None
        else None,
        "engine": str(metadata.get("engine") or metadata.get("model"))
        if (metadata.get("engine") or metadata.get("model")) is not None
        else None,
    }

    # Convertir todo el metadata a JSON convirtiendo tipos no serializables si los hay
    try:
        known_fields["raw_frontmatter_json"] = json.dumps(
            metadata, ensure_ascii=False, default=str
        )
    except Exception:
        known_fields["raw_frontmatter_json"] = "{}"

    return known_fields