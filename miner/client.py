from collections import deque
import json
import threading
import time
from typing import Any, List, Optional
import httpx


class TokenPool:
    """Pool thread-safe para distribuir y usar múltiples tokens de GitHub en paralelo."""

    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self._lock = threading.Lock()
        self._index = 0

    def get_token(self) -> str:
        with self._lock:
            token = self.tokens[self._index % len(self.tokens)]
            self._index += 1
            return token


class GitHubClient:

    def __init__(
        self, tokens: List[str], timeout: float = 15.0, max_retries: int = 3
    ):
        if not tokens:
            raise ValueError("Se requiere al menos un GitHub Token.")
        self.token_pool = TokenPool(tokens)
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GH-AW-Dataset-Miner",
        }

    def check_repos_batch_graphql(self, repo_full_names: List[str]) -> dict:
        """Consulta en UNA sola petición GraphQL si hasta 50 repositorios tienen archivos

        en .github/workflows.
        """
        token = self.token_pool.get_token()

        # Construir query GraphQL dinámica
        query_parts = []
        for idx, repo_name in enumerate(repo_full_names):
            parts = repo_name.split("/")
            if len(parts) != 2:
                continue
            owner, repo = parts[0], parts[1]

            # Alias válido para GraphQL
            alias = f"repo_{idx}"
            query_parts.append(
                f"""
                {alias}: repository(owner: "{owner}", name: "{repo}") {{
                    nameWithOwner
                    object(expression: "HEAD:.github/workflows") {{
                        ... on Tree {{
                            entries {{
                                name
                                type
                            }}
                        }}
                    }}
                }}
            """
            )

        graphql_query = "query {\n" + "\n".join(query_parts) + "\n}"

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        "https://api.github.com/graphql",
                        json={"query": graphql_query},
                        headers=self._get_headers(token),
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        results = {}
                        repo_data = data.get("data", {}) or {}
                        for alias, content in repo_data.items():
                            if not content:
                                continue
                            full_name = content.get("nameWithOwner")
                            tree_obj = content.get("object")
                            entries = []
                            if tree_obj and "entries" in tree_obj:
                                entries = [
                                    e["name"] for e in tree_obj["entries"]
                                ]
                            if full_name:
                                results[full_name] = entries
                        return results

                    elif (
                        resp.status_code == 403
                        or "rate limit" in resp.text.lower()
                    ):
                        time.sleep(2 * (attempt + 1))
                        token = (
                            self.token_pool.get_token()
                        )  # Cambiar a otro token
                    else:
                        break
            except Exception:
                time.sleep(1)

        return {}

    def get_file_content(
        self, repo_full_name: str, path: str
    ) -> Optional[str]:
        """Obtiene el contenido raw de un archivo (REST API)."""
        token = self.token_pool.get_token()
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers=self._get_headers(token))
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("encoding") == "base64":
                            import base64

                            return base64.b64decode(
                                data.get("content", "")
                            ).decode("utf-8", errors="replace")
                        return data.get("content", "")
                    elif resp.status_code in [403, 429]:
                        time.sleep(2 * (attempt + 1))
                        token = self.token_pool.get_token()
                    else:
                        break
            except Exception:
                time.sleep(1)
        return None