# Diccionario de Datos del Dataset GH-AW

### Tabla: `repositories`
| Columna | Tipo de Dato | Rol | Descripción |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | **PK** | Identificador único del repositorio en el dataset. |
| `full_name` | String | | Nombre completo del repositorio (`owner/repo`). |

### Tabla: `workflows`
| Columna | Tipo de Dato | Rol | Descripción |
| :--- | :--- | :--- | :--- |
| `id` | String (UUID) | **PK** | Identificador único del workflow. |
| `repository_id` | String (UUID) | **FK** | Referencia a `repositories.id`. |
| `filename` | String | | Nombre del archivo Markdown en `.github/workflows/`. |
| `title` | String | | Título definido en el Frontmatter. |
| `description` | String | | Descripción corta del workflow. |
| `engine` | String | | Modelo o motor configurado para el agente. |
| `raw_frontmatter_json` | String (JSON) | | Todos los campos raw del Frontmatter YAML en JSON. |

### Tabla: `workflow_bodies`
| Columna | Tipo de Dato | Rol | Descripción |
| :--- | :--- | :--- | :--- |
| `workflow_id` | String (UUID) | **PK, FK** | Referencia a `workflows.id` (Relación 1:1). |
| `body_markdown` | String | | Contenido completo en Markdown (Body) del workflow. |