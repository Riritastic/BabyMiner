import uuid
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


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