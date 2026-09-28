import json
from typing import Any, Dict, Tuple
import frontmatter


def stringify_keys(obj: Any) -> Any:
    """Asegura de forma recursiva que todas las claves de diccionarios/listas

    sean estrictamente de tipo 'str' para evitar 'keywords must be strings'
    al desempaquetar kwargs (**dict) o serializar JSON.
    """
    if isinstance(obj, dict):
        return {str(k): stringify_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_keys(elem) for elem in obj]
    return obj


def parse_workflow_md(content: str) -> Tuple[dict, str]:
    """Parsea el contenido de un archivo Markdown con Frontmatter.

    Garantiza que el diccionario de metadatos tenga claves 100% de tipo str.
    """
    if not content or not isinstance(content, str):
        return {}, ""

    try:
        post = frontmatter.loads(content)

        clean_metadata: Dict[str, Any] = {}
        if isinstance(post.metadata, dict):
            sanitized = stringify_keys(post.metadata)
            if isinstance(sanitized, dict):
                clean_metadata = sanitized

        body = post.content if isinstance(post.content, str) else str(post.content)
        return clean_metadata, body.strip()

    except Exception:
        # Si el frontmatter está corrupto o malformado, devolvemos un dict vacío y el texto plano
        return {}, content.strip()


def extract_metadata_fields(metadata: dict) -> Dict[str, Any]:
    """Extrae campos conocidos del frontmatter y empaqueta el resto en JSON string.

    Garantiza que todas las llaves del diccionario resultante sean 'str'.
    """
    # 1. Aseguramos que la entrada sea un diccionario con llaves saneadas
    clean_meta = stringify_keys(metadata) if isinstance(metadata, dict) else {}

    # 2. Extraer campos conocidos
    known_fields: Dict[str, Any] = {
        "title": (
            str(clean_meta.get("title"))
            if clean_meta.get("title") is not None
            else None
        ),
        "description": (
            str(clean_meta.get("description"))
            if clean_meta.get("description") is not None
            else None
        ),
        "engine": (
            str(clean_meta.get("engine") or clean_meta.get("model"))
            if (clean_meta.get("engine") or clean_meta.get("model")) is not None
            else None
        ),
    }

    # 3. Serialización segura a JSON String para Parquet
    try:
        known_fields["raw_frontmatter_json"] = json.dumps(
            clean_meta, ensure_ascii=False, default=str
        )
    except Exception:
        known_fields["raw_frontmatter_json"] = "{}"

    # Retornamos el diccionario garantizando que las llaves sean str puros para **kwargs
    return stringify_keys(known_fields)


# Alias para mantener compatibilidad con miner/processor.py
sanitize_dict_keys = stringify_keys