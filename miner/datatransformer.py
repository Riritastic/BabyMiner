from pathlib import Path
import pandas as pd

# Rutas
PARQUET_DIR = Path("repositories.ghaw.csv")
ORIGINAL_CSV = "results.csv"
OUTPUT_PARQUET = "ghaw_only_repositories.parquet"

# 1. Cargar el Parquet de positivos extraído por Miner
df_positives = pd.read_parquet(PARQUET_DIR / "repositories.parquet")
positive_repo_names = set(df_positives["full_name"].unique())

# 2. Cargar el CSV original de entrada
df_original = pd.read_csv(ORIGINAL_CSV)

# 3. Filtrar manteniendo SOLO los repositorios positivos
df_ghaw_only = df_original[
    df_original["name"].isin(positive_repo_names)
].copy()

# 4. Guardar en formato Parquet
df_ghaw_only.to_parquet(OUTPUT_PARQUET, index=False, engine="pyarrow")

print(f"✅ Archivo Parquet generado exitosamente: {OUTPUT_PARQUET}")
print(f"  - Total de repositorios que SÍ usan GH-AW: {len(df_ghaw_only)}")