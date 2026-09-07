import json
from typing import Any, Dict, Tuple
import frontmatter


def sanitize_dict_keys(d: Any) -> Any:
    """Asegura recursivamente que todas las claves de un diccionario sean de tipo str."""
    if isinstance(d, dict):
        return {str(k): sanitize_dict_keys(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [sanitize_dict_keys(i) for i in d]
    return d


def parse_workflow_md(content: str) -> Tuple[dict, str]:
    """Parsea el contenido de un archivo Markdown con Frontmatter.

    Garantiza que el diccionario de metadatos tenga claves 100% str.
    """
    post = frontmatter.loads(content)

    clean_metadata: Dict[str, Any] = {}
    if isinstance(post.metadata, dict):
        sanitized = sanitize_dict_keys(post.metadata)
        if isinstance(sanitized, dict):
            clean_metadata = sanitized

    body = post.content if isinstance(post.content, str) else str(post.content)
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

    try:
        known_fields["raw_frontmatter_json"] = json.dumps(
            metadata, ensure_ascii=False, default=str
        )
    except Exception:
        known_fields["raw_frontmatter_json"] = "{}"

    return known_fields