import os
import time
from itertools import cycle
from typing import List, Optional
import httpx
from dotenv import load_dotenv

from miner.models import RepositoryItem

load_dotenv()


class GitHubClient:

    def __init__(self, tokens: Optional[List[str]] = None):
        if not tokens:
            tokens_str = os.getenv("GITHUB_TOKENS", "")
            tokens = [t.strip() for t in tokens_str.split(",") if t.strip()]

        if not tokens:
            single_token = os.getenv("GITHUB_TOKEN")
            if single_token and single_token.strip():
                tokens = [single_token.strip()]

        if not tokens:
            raise ValueError(
                "No se encontraron tokens válidos en las variables de entorno (.env). "
                "Asegúrate de definir GITHUB_TOKEN o GITHUB_TOKENS."
            )

        self._token_pool = cycle(tokens)

    def _get_headers(self) -> dict:
        token = next(self._token_pool)
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_workflow_files(self, repo_full_name: str) -> List[RepositoryItem]:
        """Consulta .github/workflows/ en GitHub para obtener los nombres de archivos."""
        url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows"

        with httpx.Client(timeout=10.0) as client:
            while True:
                headers = self._get_headers()
                try:
                    response = client.get(url, headers=headers)

                    # Manejo de límites de cuota (Rate Limit)
                    if response.status_code in (403, 429):
                        reset_time = int(
                            response.headers.get(
                                "X-RateLimit-Reset", time.time() + 60
                            )
                        )
                        time.sleep(max(reset_time - int(time.time()), 2) + 1)
                        continue

                    if response.status_code != 200:
                        return []

                    items = response.json()
                    if not isinstance(items, list):
                        return []

                    return [
                        RepositoryItem(
                            name=item["name"], type=item.get("type", "file")
                        )
                        for item in items
                        if "name" in item
                    ]

                except httpx.HTTPError:
                    return []