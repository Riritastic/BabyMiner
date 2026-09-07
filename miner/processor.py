from pathlib import Path
import pandas as pd
from miner.client import GitHubClient
from miner.detector import is_gh_aw_workflow
from miner.models import Repository, WorkflowBody, WorkflowMetadata
from miner.parser import extract_metadata_fields, parse_workflow_md


class DatasetProcessor:

    def __init__(self, client: GitHubClient, repo_column: str = "name"):
        self.client = client
        self.repo_column = repo_column

    def process_and_export_parquet(
        self, input_csv: str, output_dir: Path
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        df_input = pd.read_csv(input_csv)

        repos_data = []
        workflows_data = []
        bodies_data = []

        for repo_name in df_input[self.repo_column].dropna().unique():
            items = self.client.get_workflow_files(repo_name)
            filenames = [item.name for item in items if item.type == "file"]

            # Verificar criterio Tarea 2: existe al menos un par .md y .lock.yml
            if not is_gh_aw_workflow(filenames):
                continue

            repo_entity = Repository(full_name=repo_name)
            repos_data.append(repo_entity.model_dump())

            # Identificar pares .md que tienen su .lock.yml
            md_files = [f for f in filenames if f.endswith(".md")]

            for md_file in md_files:
                base_name = md_file[:-3]
                if f"{base_name}.lock.yml" in filenames:
                    content = self.client.get_file_content(
                        repo_name, f".github/workflows/{md_file}"
                    )
                    if not content:
                        continue

                    metadata_dict, body_str = parse_workflow_md(content)
                    extracted = extract_metadata_fields(metadata_dict)

                    wf_entity = WorkflowMetadata(
                        repository_id=repo_entity.id,
                        filename=md_file,
                        title=extracted["title"],
                        description=extracted["description"],
                        engine=extracted["engine"],
                        raw_frontmatter_json=extracted["raw_frontmatter_json"],
                    )
                    workflows_data.append(wf_entity.model_dump())

                    body_entity = WorkflowBody(
                        workflow_id=wf_entity.id, body_markdown=body_str
                    )
                    bodies_data.append(body_entity.model_dump())

        # Crear DataFrames e Exportar a Parquet con PyArrow
        df_repos = pd.DataFrame(repos_data)
        df_workflows = pd.DataFrame(workflows_data)
        df_bodies = pd.DataFrame(bodies_data)

        df_repos.to_parquet(
            output_dir / "repositories.parquet", index=False, engine="pyarrow"
        )
        df_workflows.to_parquet(
            output_dir / "workflows.parquet", index=False, engine="pyarrow"
        )
        df_bodies.to_parquet(
            output_dir / "workflow_bodies.parquet",
            index=False,
            engine="pyarrow",
        )

        return {
            "repositories": len(df_repos),
            "workflows": len(df_workflows),
            "bodies": len(df_bodies),
        }