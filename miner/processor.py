from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from miner.client import GitHubClient
from miner.detector import is_gh_aw_workflow
from miner.models import Repository, WorkflowBody, WorkflowMetadata
from miner.parser import extract_metadata_fields, parse_workflow_md


class DatasetProcessor:

    def __init__(
        self,
        client: GitHubClient,
        repo_column: str = "name",
        max_workers: int = 10,
    ):
        self.client = client
        self.repo_column = repo_column
        self.max_workers = max_workers

    def _process_single_repo(
        self, repo_name: str
    ) -> Tuple[
        str,
        Optional[dict],
        list[dict],
        list[dict],
    ]:
        """Procesa un solo repositorio de forma aislada para ejecutar en un hilo."""
        try:
            items = self.client.get_workflow_files(repo_name)
            filenames = [item.name for item in items if item.type == "file"]

            if not is_gh_aw_workflow(filenames):
                return repo_name, None, [], []

            repo_entity = Repository(full_name=repo_name)
            repo_dict = repo_entity.model_dump()

            workflows_dicts = []
            bodies_dicts = []

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
                    workflows_dicts.append(wf_entity.model_dump())

                    body_entity = WorkflowBody(
                        workflow_id=wf_entity.id, body_markdown=body_str
                    )
                    bodies_dicts.append(body_entity.model_dump())

            return repo_name, repo_dict, workflows_dicts, bodies_dicts

        except Exception as e:
            print(f" [!] Error procesando {repo_name}: {e}")
            return repo_name, None, [], []

    def process_and_export_parquet(
        self, input_csv: str, output_dir: Path, batch_size: int = 20
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)

        repo_parquet_path = output_dir / "repositories.parquet"
        wf_parquet_path = output_dir / "workflows.parquet"
        body_parquet_path = output_dir / "workflow_bodies.parquet"

        processed_repo_names = set()
        repos_list = []
        workflows_list = []
        bodies_list = []

        # 1. CARGAR AVANCE PREVIO (SI EXISTE)
        if (
            repo_parquet_path.exists()
            and wf_parquet_path.exists()
            and body_parquet_path.exists()
        ):
            print(
                " Se encontró un avance previo en Parquet. Cargando datos..."
            )
            df_existing_repos = pd.read_parquet(repo_parquet_path)
            df_existing_wfs = pd.read_parquet(wf_parquet_path)
            df_existing_bodies = pd.read_parquet(body_parquet_path)

            processed_repo_names = set(df_existing_repos["full_name"].tolist())
            repos_list = df_existing_repos.to_dict(orient="records")
            workflows_list = df_existing_wfs.to_dict(orient="records")
            bodies_list = df_existing_bodies.to_dict(orient="records")

        # 2. LEER CSV DE ENTRADA Y FILTRAR PENDIENTES
        df_input = pd.read_csv(input_csv)
        all_candidate_repos = (
            df_input[self.repo_column].dropna().unique().tolist()
        )
        pending_repos = [
            r for r in all_candidate_repos if r not in processed_repo_names
        ]

        print(
            f" Total candidatos: {len(all_candidate_repos)} | "
            f"Ya procesados: {len(processed_repo_names)} | "
            f"Pendientes: {len(pending_repos)}"
        )

        # 3. PROCESAMIENTO EN BLOQUES (BATCHES) CON HILOS CONCURRENTES
        for i in range(0, len(pending_repos), batch_size):
            batch_repos = pending_repos[i : i + batch_size]

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._process_single_repo, repo)
                    for repo in batch_repos
                ]

                for future in as_completed(futures):
                    repo_name, repo_dict, wf_dicts, body_dicts = (
                        future.result()
                    )
                    processed_repo_names.add(repo_name)

                    if repo_dict:
                        repos_list.append(repo_dict)
                        workflows_list.extend(wf_dicts)
                        bodies_list.extend(body_dicts)

            # GUARDADO INCREMENTAL AL COMPLETAR CADA LOTE
            pd.DataFrame(repos_list).to_parquet(
                repo_parquet_path, index=False, engine="pyarrow"
            )
            pd.DataFrame(workflows_list).to_parquet(
                wf_parquet_path, index=False, engine="pyarrow"
            )
            pd.DataFrame(bodies_list).to_parquet(
                body_parquet_path, index=False, engine="pyarrow"
            )

            processed_count = min(i + batch_size, len(pending_repos))
            print(
                f" Progreso: {processed_count}/{len(pending_repos)} repositorios "
                f"pendientes procesados (Avance guardado en Parquet)."
            )

        return {
            "repositories": len(repos_list),
            "workflows": len(workflows_list),
            "bodies": len(bodies_list),
        }