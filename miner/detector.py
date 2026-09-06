from typing import Iterable


def is_gh_aw_workflow(filenames: Iterable[str]) -> bool:
    """Verifica si entre la lista de archivos existe al menos un par 'nombre.md'

    y 'nombre.lock.yml'.
    """
    files_set = set(filenames)

    # Nombres base de los archivos Markdown (.md)
    md_bases = {f[:-3] for f in files_set if f.endswith(".md")}

    # Comprobar si existe el archivo .lock.yml correspondiente
    for base_name in md_bases:
        if f"{base_name}.lock.yml" in files_set:
            return True

    return False