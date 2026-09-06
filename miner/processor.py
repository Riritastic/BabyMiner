from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from miner.client import GitHubClient
from miner.detector import is_gh_aw_workflow


class RepositoryProcessor:

    def __init__(
        self,
        client: GitHubClient,
        repo_column: str = "name",
        max_workers: int = 10,
    ):
        self.client = client
        self.repo_column = repo_column
        self.max_workers = max_workers

    def _check_repo(self, repo_full_name: str) -> tuple[str, bool]:
        items = self.client.get_workflow_files(repo_full_name)
        filenames = [
            item.name for item in items if item.type in ("file", "blob")
        ]
        uses_aw = is_gh_aw_workflow(filenames)
        return repo_full_name, uses_aw

    def process(self, input_path: str, output_path: str) -> int:
        """Lee el CSV candidato, procesa los repositorios y guarda únicamente los que usan GH-AW."""
        df = pd.read_csv(input_path)

        if self.repo_column not in df.columns:
            raise KeyError(
                f"La columna '{self.repo_column}' no existe en el CSV de entrada."
            )

        repos = df[self.repo_column].dropna().unique().tolist()
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._check_repo, repo) for repo in repos
            ]
            for future in as_completed(futures):
                repo_name, uses_aw = future.result()
                results[repo_name] = uses_aw

        # Agregar columna temporal de filtrado
        df["_uses_gh_aw"] = df[self.repo_column].map(results).fillna(False)

        # Filtrar solo los que utilizan GitHub Agentic Workflows
        df_filtered = df[df["_uses_gh_aw"] == True].drop(columns=["_uses_gh_aw"])

        df_filtered.to_csv(output_path, index=False)
        return len(df_filtered)