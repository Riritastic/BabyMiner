import json
from pathlib import Path
import pandas as pd


def mix_dataset_classification(
    input_csv: str,
    output_dir: Path,
    repo_column: str = "name",
    output_file: str = "repos_classified.csv",
) -> Path:
    """Combina el CSV original de entrada con el estado de procesamiento y

    genera un dataset con la etiqueta binaria 'is_gh_aw' (1 si usa GH-AW, 0 si no).
    """
    output_dir = Path(output_dir)
    processed_log_path = output_dir / "processed_repos.json"
    repo_parquet_path = output_dir / "repositories.parquet"

    if not processed_log_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de log: {processed_log_path}"
        )

    # 1. Cargar el registro de repositorios procesados
    with open(processed_log_path, "r", encoding="utf-8") as f:
        processed_repos = set(json.load(f))

    # 2. Cargar repositorios positivos (1) desde Parquet
    gh_aw_repos = set()
    if repo_parquet_path.exists():
        try:
            df_pos = pd.read_parquet(repo_parquet_path)
            if not df_pos.empty and "full_name" in df_pos.columns:
                gh_aw_repos = set(df_pos["full_name"].tolist())
        except Exception as e:
            print(f"⚠️ Advertencia al cargar {repo_parquet_path}: {e}")

    # 3. Cargar CSV original
    df_input = pd.read_csv(input_csv)
    if repo_column not in df_input.columns:
        raise KeyError(
            f"La columna '{repo_column}' no existe en el CSV de entrada."
        )

    # 4. Filtrar solo repositorios que ya fueron evaluados
    df_result = df_input[df_input[repo_column].isin(processed_repos)].copy()

    # 5. Agregar la clasificación binaria (1 o 0)
    df_result["is_gh_aw"] = df_result[repo_column].apply(
        lambda repo: 1 if repo in gh_aw_repos else 0
    )

    # 6. Exportar resultado
    destination_path = output_dir / output_file
    if output_file.endswith(".parquet"):
        df_result.to_parquet(
            destination_path, index=False, engine="pyarrow"
        )
    else:
        df_result.to_csv(destination_path, index=False)

    print(f"✅ Datamixer completado exitosamente -> {destination_path}")
    print(f"  - Total procesados en el dataset: {len(df_result)}")
    print(f"  - Repositorios GH-AW (1): {len(gh_aw_repos)}")
    print(f"  - Repositorios No GH-AW (0): {len(df_result) - len(gh_aw_repos)}")

    return destination_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Mezcla el CSV original con la clasificación binaria GH-AW."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        default="results.csv",
        help="Ruta al CSV original.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="repositories.ghaw.csv",
        help="Directorio donde se encuentran los parquets.",
    )
    parser.add_argument(
        "--repo-column",
        type=str,
        default="name",
        help="Columna del CSV con el owner/repo.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="repos_classified.csv",
        help="Nombre del archivo de salida (.parquet o .csv).",
    )

    args = parser.parse_args()
    mix_dataset_classification(
        input_csv=args.input_csv,
        output_dir=Path(args.output_dir),
        repo_column=args.repo_column,
        output_file=args.output_file,
    )

    #python -m miner.datamixer --input-csv results.csv --output-dir repositories.ghaw.csv --repo-column name --output-file repos_classified.csv