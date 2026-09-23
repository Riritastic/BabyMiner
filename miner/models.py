from dataclasses import dataclass
from typing import Optional


@dataclass
class RepositoryData:
    id: str
    owner: str
    name: str
    full_name: str
    stars: int
    forks: int
    open_issues: int
    main_language: Optional[str]
    is_archived: bool
    created_at: str
    updated_at: str
    last_commit_at: Optional[str]
    default_branch: str


@dataclass
class WorkflowData:
    id: str
    repository_id: str
    md_path: str
    md_filename: str
    title: Optional[str]
    description: Optional[str]
    engine: Optional[str]
    is_gh_aw: bool = True


@dataclass
class WorkflowMarkdownData:
    """Artefacto PRIMARIO (Entrada/Definición): El archivo .md ejecutable."""

    workflow_id: str
    raw_markdown: str
    frontmatter_yaml: Optional[str]


@dataclass
class WorkflowBodyData:
    """Cuerpo de instrucciones del prompt extraído del Markdown primario."""

    workflow_id: str
    body_markdown: str
    word_count: int


@dataclass
class WorkflowYmlData:
    """Artefacto SECUNDARIO (Salida/Generado 1:1): El YAML compilado resultante."""

    workflow_id: str
    generated_yml_path: Optional[str]
    raw_yml_content: Optional[str]
    parsed_yaml_json: Optional[str]