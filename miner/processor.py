from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from typing import List, Tuple
import pandas as pd

from miner.client import GitHubClient
from miner.detector import is_gh_aw_workflow
from miner.models import Repository, WorkflowBody, WorkflowMetadata
from miner.parser import (
    extract_metadata_fields,
    parse_workflow_md,
    sanitize_dict_keys,
)


class DatasetProcessor:

    def __init__(
        self,
        client: GitHubClient,
        repo_column: str = "name",
        max_workers: int = 15,
    ):
        self.client = client
        self.repo_column = repo_column
        self.max_workers = max_workers

    def _process_single_gh_aw_repo(
        self, repo_name: str, filenames: List[str]
    ) -> Tuple[dict, list[dict], list[dict]]:
        """Descarga el contenido completo únicamente para repositorios con GH-AW."""
        repo_entity = Repository(full_name=repo_name)
        repo_dict = sanitize_dict_keys(repo_entity.model_dump())

        workflows_dicts = []
        bodies_dicts = []

        md_files = [f for f in filenames if f.endswith(".md")]
        for md_file in md_files:
            base_name = md_file[:-3]
            if f"{base_name}.lock.yml" in filenames:
                try:
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
                    workflows_dicts.append(
                        sanitize_dict_keys(wf_entity.model_dump())
                    )

                    body_entity = WorkflowBody(
                        workflow_id=wf_entity.id, body_markdown=body_str
                    )
                    bodies_dicts.append(
                        sanitize_dict_keys(body_entity.model_dump())
                    )

                except Exception as file_err:
                    print(
                        f"  [!] Omitiendo {md_file} en {repo_name}: {file_err}"
                    )
                    continue

        return repo_dict, workflows_dicts, bodies_dicts

    def process_and_export_parquet(
        self, input_csv: str, output_dir: Path, batch_size: int = 50
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

        # 1. CARGAR REGISTRO Y PARQUETS PREVIOS
        if processed_log_path.exists():
            try:
                with open(processed_log_path, "r", encoding="utf-8") as f:
                    processed_repo_names = set(json.load(f))
            except Exception:
                processed_repo_names = set()

        if repo_parquet_path.exists():
            try:
                df = pd.read_parquet(repo_parquet_path)
                if not df.empty:
                    repos_list = df.to_dict(orient="records")
            except Exception:
                pass

        if wf_parquet_path.exists():
            try:
                df = pd.read_parquet(wf_parquet_path)
                if not df.empty:
                    workflows_list = df.to_dict(orient="records")
            except Exception:
                pass

        if body_parquet_path.exists():
            try:
                df = pd.read_parquet(body_parquet_path)
                if not df.empty:
                    bodies_list = df.to_dict(orient="records")
            except Exception:
                pass

        # 2. FILTRAR PENDIENTES
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

        # 3. PROCESAMIENTO MÁSIVO BATCHED VIA GRAPHQL (50 REPOS POR QUERY)
        # Agrupar pendientes en lotes de 50 para GraphQL
        graphql_batches = [
            pending_repos[i : i + batch_size]
            for i in range(0, len(pending_repos), batch_size)
        ]

        print(
            f" Ejecutando en {len(graphql_batches)} super-lotes con {self.max_workers} hilos concurrentes en paralelo..."
        )

        processed_counter = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for batch_index in range(0, len(graphql_batches), self.max_workers):
                worker_batches = graphql_batches[
                    batch_index : batch_index + self.max_workers
                ]

                futures = [
                    executor.submit(
                        self.client.check_repos_batch_graphql, batch
                    )
                    for batch in worker_batches
                ]

                for future in as_completed(futures):
                    batch_result = future.result()

                    # Inspeccionar resultados del super-lote
                    for repo_name, filenames in batch_result.items():
                        processed_repo_names.add(repo_name)

                        # Verificar si tiene workflows GH-AW
                        if is_gh_aw_workflow(filenames):
                            r_dict, w_dicts, b_dicts = (
                                self._process_single_gh_aw_repo(
                                    repo_name, filenames
                                )
                            )
                            if r_dict:
                                repos_list.append(r_dict)
                                workflows_list.extend(w_dicts)
                                bodies_list.extend(b_dicts)

                # Asegurar de marcar todos los repos del super-lote como evaluados
                for batch in worker_batches:
                    processed_repo_names.update(batch)
                    processed_counter += len(batch)

                # GUARDAR AVANCE TRAS CADA SUPER-LOTE DE WORKERS
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

                with open(processed_log_path, "w", encoding="utf-8") as f:
                    json.dump(list(processed_repo_names), f)

                print(
                    f" Progreso acelerado: {processed_counter}/{len(pending_repos)} repositorios "
                    f"evaluados (Encontrados: {len(repos_list)} repos GH-AW)."
                )

        return {
            "repositories": len(repos_list),
            "workflows": len(workflows_list),
            "bodies": len(bodies_list),
        }