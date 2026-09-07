# Modelo Entidad-Relación

```mermaid
erDiagram
    REPOSITORIES ||--o{ WORKFLOWS : "contiene"
    WORKFLOWS ||--|| WORKFLOW_BODIES : "posee"

    REPOSITORIES {
        string id PK
        string full_name
    }

    WORKFLOWS {
        string id PK
        string repository_id FK
        string filename
        string title
        string description
        string engine
        string raw_frontmatter_json
    }

    WORKFLOW_BODIES {
        string workflow_id PK_FK
        string body_markdown
    }