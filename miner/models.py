import uuid
from typing import Optional
from pydantic import BaseModel, Field


# --- Modelo utilizado por el cliente de GitHub (Tarea 2 / Tarea 3) ---
class RepositoryItem(BaseModel):
    """Representa un archivo o directorio dentro del repositorio."""

    name: str
    type: str = Field(
        default="file", description="Tipo de ítem: 'file' o 'dir'"
    )


# --- Modelos del Dataset / Parquet (Tarea 3) ---
class Repository(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    full_name: str


class WorkflowMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    filename: str
    title: Optional[str] = None
    description: Optional[str] = None
    engine: Optional[str] = None
    raw_frontmatter_json: Optional[str] = (
        None  # Resguardo de campos dinámicos en JSON
    )


class WorkflowBody(BaseModel):
    workflow_id: str
    body_markdown: str