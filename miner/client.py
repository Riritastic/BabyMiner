from collections import deque
import json
import threading
import time
from typing import Any, Dict, List, Optional
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
        self, tokens: List[str], timeout: float = 20.0, max_retries: int = 3
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

    def fetch_repos_and_workflows_batch_graphql(
        self, repo_full_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Consulta en UNA sola petición GraphQL las métricas extendidas del repositorio

        y el árbol de archivos en `.github/` para extraer los Markdown primarios
        y sus YAMLs secundarios generados.
        """
        token = self.token_pool.get_token()

        # Construcción de la consulta GraphQL extendida por repositorio
        query_parts = []
        for idx, repo_name in enumerate(repo_full_names):
            parts = repo_name.split("/")
            if len(parts) != 2:
                continue
            owner, repo = parts[0], parts[1]
            alias = f"repo_{idx}"

            query_parts.append(
                f"""
                {alias}: repository(owner: "{owner}", name: "{repo}") {{
                    id
                    name
                    nameWithOwner
                    stargazerCount
                    forkCount
                    isArchived
                    createdAt
                    updatedAt
                    pushedAt
                    owner {{
                        login
                    }}
                    primaryLanguage {{
                        name
                    }}
                    defaultBranchRef {{
                        name
                        target {{
                            ... on Commit {{
                                committedDate
                            }}
                        }}
                    }}
                    issues(states: OPEN) {{
                        totalCount
                    }}
                    github_dir: object(expression: "HEAD:.github") {{
                        ... on Tree {{
                            entries {{
                                name
                                path
                                type
                                object {{
                                    ... on Blob {{
                                        text
                                    }}
                                }}
                            }}
                        }}
                    }}
                    workflows_dir: object(expression: "HEAD:.github/workflows") {{
                        ... on Tree {{
                            entries {{
                                name
                                path
                                type
                                object {{
                                    ... on Blob {{
                                        text
                                    }}
                                }}
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
                            if not full_name:
                                continue

                            # 1. Extraer métricas extendidas del Repositorio
                            default_branch = ""
                            last_commit_at = None
                            branch_ref = content.get("defaultBranchRef")
                            if branch_ref:
                                default_branch = branch_ref.get("name", "")
                                target = branch_ref.get("target") or {}
                                last_commit_at = target.get("committedDate")

                            repo_info = {
                                "id": content.get("id"),
                                "owner": content.get("owner", {}).get("login"),
                                "name": content.get("name"),
                                "full_name": full_name,
                                "stars": content.get("stargazerCount", 0),
                                "forks": content.get("forkCount", 0),
                                "open_issues": content.get("issues", {}).get(
                                    "totalCount", 0
                                ),
                                "main_language": (
                                    content.get("primaryLanguage") or {}
                                ).get("name"),
                                "is_archived": content.get("isArchived", False),
                                "created_at": content.get("createdAt"),
                                "updated_at": content.get("updatedAt"),
                                "last_commit_at": last_commit_at
                                or content.get("pushedAt"),
                                "default_branch": default_branch,
                            }

                            # 2. Recolectar archivos Markdown (Primarios) y YAML (Secundarios)
                            files_map = {}

                            for dir_key in ["github_dir", "workflows_dir"]:
                                tree_obj = content.get(dir_key)
                                if tree_obj and "entries" in tree_obj:
                                    for entry in tree_obj["entries"]:
                                        if entry.get("type") == "blob":
                                            file_name = entry.get("name")
                                            file_path = entry.get("path")
                                            blob_obj = entry.get(
                                                "object"
                                            ) or {}
                                            text_content = blob_obj.get(
                                                "text", ""
                                            )
                                            files_map[file_name] = {
                                                "path": file_path,
                                                "content": text_content,
                                            }

                            results[full_name] = {
                                "repository": repo_info,
                                "files": files_map,
                            }

                        return results

                    elif (
                        resp.status_code == 403
                        or "rate limit" in resp.text.lower()
                    ):
                        time.sleep(2 * (attempt + 1))
                        token = self.token_pool.get_token()
                    else:
                        break
            except Exception:
                time.sleep(1)

        return {}

    def get_file_content(
        self, repo_full_name: str, path: str
    ) -> Optional[str]:
        """Obtiene el contenido raw de un archivo mediante REST API (fallback si no vino en GraphQL)."""
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