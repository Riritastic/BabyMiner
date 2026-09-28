from pathlib import PurePosixPath
from typing import Iterable


def is_gh_aw_workflow(filenames: Iterable[str]) -> bool:
    """Verifica si entre la lista de archivos existe al menos un par
    'nombre.md' y su correspondiente 'nombre.lock.yml' (o .lock.yaml).
    """
    # Normalizar rutas a formato POSIX (slash /) para evitar inconsistencias de OS
    normalized_files = {
        PurePosixPath(f).as_posix() for f in filenames if isinstance(f, str)
    }

    # Filtrar solo archivos Markdown
    md_files = [f for f in normalized_files if f.endswith(".md")]

    for md_path_str in md_files:
        md_path = PurePosixPath(md_path_str)

        # Nombre base sin extensión .md
        stem = md_path.stem
        parent = md_path.parent

        # Generar las posibles rutas del archivo lock compilado
        # Soporta tanto .lock.yml como .lock.yaml
        lock_yml = (
            (parent / f"{stem}.lock.yml").as_posix()
            if parent != PurePosixPath(".")
            else f"{stem}.lock.yml"
        )
        lock_yaml = (
            (parent / f"{stem}.lock.yaml").as_posix()
            if parent != PurePosixPath(".")
            else f"{stem}.lock.yaml"
        )

        if lock_yml in normalized_files or lock_yaml in normalized_files:
            return True

    return False