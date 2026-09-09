import json
import pandas as pd
from pathlib import Path

# Cargar CSV original y registro de procesados
df_input = pd.read_csv("repos.csv")  # Tu CSV original
output_dir = Path("dataset_parquet")

with open(output_dir / "processed_repos.json", "r", encoding="utf-8") as f:
    processed_repos = set(json.load(f))

# Cargar repositorios positivos desde el Parquet
df_positives = pd.read_parquet(output_dir / "repositories.parquet")
gh_aw_repos = set(df_positives["full_name"].tolist())

# Filtrar solo los repositorios que ya fueron evaluados
df_result = df_input[df_input["name"].isin(processed_repos)].copy()

# Crear la columna de clasificación binaria
df_result["is_gh_aw"] = df_result["name"].apply(
    lambda repo: 1 if repo in gh_aw_repos else 0
)

# Exportar a CSV o Parquet completo
df_result.to_parquet("repos_classified.parquet", index=False)
print("Clasificación completada:")
print(df_result["is_gh_aw"].value_counts())