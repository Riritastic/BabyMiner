from pydantic import BaseModel, Field


class RepositoryItem(BaseModel):
    """Representa un archivo o directorio dentro del repositorio."""

    name: str
    type: str = Field(..., description="Tipo de ítem: 'file' o 'dir'")


class RepositoryInfo(BaseModel):
    """Representa la información base de un repositorio."""

    full_name: str
    uses_gh_aw: bool = False