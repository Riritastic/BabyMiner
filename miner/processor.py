from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd

from miner.client import GitHubClient
from miner.detector import is_gh_aw_workflow
from miner.models import (
    RepositoryData,
    WorkflowBodyData,
    WorkflowData,
    WorkflowMarkdownData,
    WorkflowYmlData,
)
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
        self, repo_info: dict, files_map: dict
    ) -> Tuple[dict, List[dict], List[dict], List[dict], List[dict]]:
        """Procesa los archivos de un repositorio para extraer los Markdown primarios

        y vincular 1:1 sus YAMLs compilados resultantes.
        """
        # Instanciar entidad Repository
        repo_entity = RepositoryData(**repo_info)
        repo_dict = sanitize_dict_keys(repo_entity.__dict__)

        workflows_dicts = []
        markdown_dicts = []
        bodies_dicts = []
        yml_dicts = []

        filenames = list(files_map.keys())
        md_files = [f for f in filenames if f.endswith(".md")]

        for md_file in md_files:
            base_name = md_file[:-3]
            lock_yml_name = f"{base_name}.lock.yml"

            # Verificar si existe la pareja Markdown -> YAML compilado (1:1)
            if lock_yml_name in filenames:
                try:
                    md_file_info = files_map[md_file]
                    yml_file_info = files_map[lock_yml_name]

                    raw_md_content = md_file_info.get("content", "")
                    raw_yml_content = yml_file_info.get("content", "")

                    if not raw_md_content:
                        continue

                    # 1. Parsear el Markdown primario
                    metadata_dict, body_str = parse_workflow_md(raw_md_content)
                    extracted = extract_metadata_fields(metadata_dict)

                    # 2. Entidad Workflow (Nodo Central)
                    wf_entity = WorkflowData(
                        id=f"{repo_entity.id}_{md_file}",
                        repository_id=repo_entity.id,
                        md_path=md_file_info.get("path", md_file),
                        md_filename=md_file,
                        title=extracted.get("title"),
                        description=extracted.get("description"),
                        engine=extracted.get("engine"),
                        is_gh_aw=True,
                    )
                    workflows_dicts.append(
                        sanitize_dict_keys(wf_entity.__dict__)
                    )

                    # 3. Entidad WorkflowMarkdown (Artefacto Primario)
                    md_entity = WorkflowMarkdownData(
                        workflow_id=wf_entity.id,
                        raw_markdown=raw_md_content,
                        frontmatter_yaml=extracted.get("raw_frontmatter_json"),
                    )
                    markdown_dicts.append(
                        sanitize_dict_keys(md_entity.__dict__)
                    )

                    # 4. Entidad WorkflowBody (Cuerpo/Prompt)
                    body_entity = WorkflowBodyData(
                        workflow_id=wf_entity.id,
                        body_markdown=body_str,
                        word_count=len(body_str.split()),
                    )
                    bodies_dicts.append(
                        sanitize_dict_keys(body_entity.__dict__)
                    )

                    # 5. Entidad WorkflowYml (Artefacto Secundario Compilado 1:1)
                    parsed_yaml_json = None
                    try:
                        import yaml

                        parsed_dict = yaml.safe_load(raw_yml_content)
                        parsed_yaml_json = json.dumps(
                            parsed_dict, ensure_ascii=False
                        )
                    except Exception:
                        parsed_yaml_json = None

                    yml_entity = WorkflowYmlData(
                        workflow_id=wf_entity.id,
                        generated_yml_path=yml_file_info.get(
                            "path", lock_yml_name
                        ),
                        raw_yml_content=raw_yml_content,
                        parsed_yaml_json=parsed_yaml_json,
                    )
                    yml_dicts.append(sanitize_dict_keys(yml_entity.__dict__))

                except Exception as file_err:
                    print(
                        f"  [!] Omitiendo {md_file} en {repo_info.get('full_name')}: {file_err}"
                    )
                    continue

        return (
            repo_dict,
            workflows_dicts,
            markdown_dicts,
            bodies_dicts,
            yml_dicts,
        )

    def process_and_export_parquet(
        self, input_csv: str, output_dir: Path, batch_size: int = 50
    ) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)

        repo_parquet_path = output_dir / "repositories.parquet"
        wf_parquet_path = output_dir / "workflows.parquet"
        md_parquet_path = output_dir / "workflow_markdown.parquet"
        body_parquet_path = output_dir / "workflow_bodies.parquet"
        yml_parquet_path = output_dir / "workflow_yml.parquet"
        processed_log_path = output_dir / "processed_repos.json"

        processed_repo_names = set()
        repos_list = []
        workflows_list = []
        markdown_list = []
        bodies_list = []
        yml_list = []

        # 1. CARGAR REGISTRO Y PARQUETS PREVIOS
        if processed_log_path.exists():
            try:
                with open(processed_log_path, "r", encoding="utf-8") as f:
                    processed_repo_names = set(json.load(f))
            except Exception:
                processed_repo_names = set()

        def _load_existing_parquet(path: Path) -> list:
            if path.exists():
                try:
                    df = pd.read_parquet(path)
                    if not df.empty:
                        return df.to_dict(orient="records")
                except Exception:
                    pass
            return []

        repos_list = _load_existing_parquet(repo_parquet_path)
        workflows_list = _load_existing_parquet(wf_parquet_path)
        markdown_list = _load_existing_parquet(md_parquet_path)
        bodies_list = _load_existing_parquet(body_parquet_path)
        yml_list = _load_existing_parquet(yml_parquet_path)

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

        # 3. PROCESAMIENTO MASIVO BATCHED VIA GRAPHQL
        graphql_batches = [
            pending_repos[i : i + batch_size]
            for i in range(0, len(pending_repos), batch_size)
        ]

        print(
            f" Ejecutando en {len(graphql_batches)} super-lotes con {self.max_workers} hilos concurrentes..."
        )

        processed_counter = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for batch_index in range(0, len(graphql_batches), self.max_workers):
                worker_batches = graphql_batches[
                    batch_index : batch_index + self.max_workers
                ]

                futures = [
                    executor.submit(
                        self.client.fetch_repos_and_workflows_batch_graphql,
                        batch,
                    )
                    for batch in worker_batches
                ]

                for future in as_completed(futures):
                    batch_result = future.result()

                    for full_name, repo_data in batch_result.items():
                        processed_repo_names.add(full_name)

                        repo_info = repo_data.get("repository", {})
                        files_map = repo_data.get("files", {})
                        filenames = list(files_map.keys())

                        if is_gh_aw_workflow(filenames):
                            (
                                r_dict,
                                w_dicts,
                                md_dicts,
                                b_dicts,
                                y_dicts,
                            ) = self._process_single_gh_aw_repo(
                                repo_info, files_map
                            )

                            if r_dict and w_dicts:
                                repos_list.append(r_dict)
                                workflows_list.extend(w_dicts)
                                markdown_list.extend(md_dicts)
                                bodies_list.extend(b_dicts)
                                yml_list.extend(y_dicts)

                for batch in worker_batches:
                    processed_repo_names.update(batch)
                    processed_counter += len(batch)

                # GUARDAR AVANCE (5 TABLAS)
                if repos_list:
                    pd.DataFrame(repos_list).to_parquet(
                        repo_parquet_path, index=False, engine="pyarrow"
                    )
                if workflows_list:
                    pd.DataFrame(workflows_list).to_parquet(
                        wf_parquet_path, index=False, engine="pyarrow"
                    )
                if markdown_list:
                    pd.DataFrame(markdown_list).to_parquet(
                        md_parquet_path, index=False, engine="pyarrow"
                    )
                if bodies_list:
                    pd.DataFrame(bodies_list).to_parquet(
                        body_parquet_path, index=False, engine="pyarrow"
                    )
                if yml_list:
                    pd.DataFrame(yml_list).to_parquet(
                        yml_parquet_path, index=False, engine="pyarrow"
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
            "workflow_markdown": len(markdown_list),
            "workflow_bodies": len(bodies_list),
            "workflow_yml": len(yml_list),
        }