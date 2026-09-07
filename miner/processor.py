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
        processed_log_path = output_dir / "processed_repos.json"

        processed_repo_names = set()
        repos_list = []
        workflows_list = []
        bodies_list = []

        # 1. CARGAR REGISTRO DE REPOS PROCESADOS (SI EXISTE)
        if processed_log_path.exists():
            try:
                with open(processed_log_path, "r", encoding="utf-8") as f:
                    processed_repo_names = set(json.load(f))
            except Exception:
                processed_repo_names = set()

        # 2. CARGAR AVANCES EN PARQUET SI EXISTEN
        if repo_parquet_path.exists():
            try:
                df_existing = pd.read_parquet(repo_parquet_path)
                if not df_existing.empty and "full_name" in df_existing.columns:
                    repos_list = df_existing.to_dict(orient="records")
            except Exception:
                repos_list = []

        if wf_parquet_path.exists():
            try:
                df_existing = pd.read_parquet(wf_parquet_path)
                if not df_existing.empty:
                    workflows_list = df_existing.to_dict(orient="records")
            except Exception:
                workflows_list = []

        if body_parquet_path.exists():
            try:
                df_existing = pd.read_parquet(body_parquet_path)
                if not df_existing.empty:
                    bodies_list = df_existing.to_dict(orient="records")
            except Exception:
                bodies_list = []

        # 3. LEER CSV DE ENTRADA Y FILTRAR PENDIENTES
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

        # 4. PROCESAMIENTO EN BATCHES
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

            # GUARDAR AVANCE EN DISCO AL COMPLETAR CADA LOTE
            if repos_list:
                pd.DataFrame(repos_list).to_parquet(
                    repo_parquet_path, index=False, engine="pyarrow"
                )
            if workflows_list:
                pd.DataFrame(workflows_list).to_parquet(
                    wf_parquet_path, index=False, engine="pyarrow"
                )
            if bodies_list:
                pd.DataFrame(bodies_list).to_parquet(
                    body_parquet_path, index=False, engine="pyarrow"
                )

            # Guardar lista completa de procesados (para saber que no hay que reevaluarlos)
            with open(processed_log_path, "w", encoding="utf-8") as f:
                json.dump(list(processed_repo_names), f)

            processed_count = min(i + batch_size, len(pending_repos))
            print(
                f" Progreso: {processed_count}/{len(pending_repos)} repositorios "
                f"pendientes procesados (Avance guardado)."
            )

        return {
            "repositories": len(repos_list),
            "workflows": len(workflows_list),
            "bodies": len(bodies_list),
        }