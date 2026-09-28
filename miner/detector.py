from pathlib import PurePosixPath
from typing import Iterable


def is_gh_aw_workflow(filenames: Iterable[str]) -> bool:
    """Verifica si en el repositorio existe la pareja 'nombre.md' y 'nombre.lock.yml'

    ubicada estrictamente dentro de la ruta '.github/workflows/'.
    """
    normalized_files = set()

    # 1. Normalizar todas las rutas a separadores Unix (/)
    for f in filenames:
        if isinstance(f, str):
            # Convertir cualquier backlash (\) a slash (/)
            path_str = f.replace("\\", "/").strip("/")
            normalized_files.add(path_str)

    # 2. Filtrar solo los archivos .md que estén en .github/workflows/
    # (o que se llamen .md si la query GraphQL ya filtra por la carpeta workflows)
    aw_md_bases = set()

    for path in normalized_files:
        p = PurePosixPath(path)

        # Si viene con la ruta completa .github/workflows/
        if "github/workflows" in path.lower() and p.suffix == ".md":
            # Extraer la ruta base sin extensión .md
            # ej: '.github/workflows/daily-report'
            aw_md_bases.add(str(p.parent / p.stem))

        # Si GraphQL trajo únicamente el nombre del archivo simple (ej: 'daily-report.md')
        elif len(p.parts) == 1 and p.suffix == ".md":
            aw_md_bases.add(p.stem)

    # 3. Validar si existe el archivo .lock.yml correspondiente para esa misma base
    for base in aw_md_bases:
        target_lock_1 = f"{base}.lock.yml"
        target_lock_2 = f"{base}.lock.yaml"

        if target_lock_1 in normalized_files or target_lock_2 in normalized_files:
            return True

    return False