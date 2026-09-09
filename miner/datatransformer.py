import argparse
from pathlib import Path
import pandas as pd


def transform_to_ghaw_only_parquet(
    input_csv: str = "results.csv",
    parquet_dir: str = "repositories.ghaw.csv",
    repo_column: str = "name",
    output_file: str = "ghaw_only_repositories.parquet",
) -> Path:
    """Filtra el CSV original para conservar ÚNICAMENTE los repositorios que utilizan GH-AW

    y lo exporta a formato Parquet.
    """
    p_dir = Path(parquet_dir)
    repo_parquet_path = p_dir / "repositories.parquet"

    if not repo_parquet_path.exists():
        raise FileNotFoundError(
            f"❌ No se encontró el Parquet de repositorios en: {repo_parquet_path}"
        )

    # 1. Cargar repositorios positivos identificados por Miner
    print(f"📖 Leyendo repositorios confirmados desde {repo_parquet_path}...")
    df_positives = pd.read_parquet(repo_parquet_path)

    if "full_name" not in df_positives.columns:
        raise KeyError(
            "La columna 'full_name' no está presente en repositories.parquet."
        )

    positive_repo_names = set(df_positives["full_name"].dropna().unique())

    # 2. Cargar CSV original
    print(f"📖 Leyendo CSV original desde {input_csv}...")
    df_original = pd.read_csv(input_csv)

    if repo_column not in df_original.columns:
        raise KeyError(
            f"La columna '{repo_column}' no existe en el archivo {input_csv}."
        )

    # 3. Filtrar para mantener SOLO los que están en la lista de positivos
    df_ghaw_only = df_original[
        df_original[repo_column].isin(positive_repo_names)
    ].copy()

    # 4. Exportar el resultado a Parquet
    destination_path = p_dir / output_file
    df_ghaw_only.to_parquet(destination_path, index=False, engine="pyarrow")

    print("\n✅ Transformación completada exitosamente.")
    print(
        f"  - Total de repositorios analizados en CSV original: {len(df_original):,}"
    )
    print(
        f"  - Repositorios filtrados (SÓLO GH-AW): {len(df_ghaw_only):,} (100% positivos)"
    )
    print(f"  - Archivo Parquet generado en: {destination_path}")

    return destination_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera un Parquet únicamente con repositorios que utilizan GH-AW."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        default="results.csv",
        help="Ruta al CSV original de entrada.",
    )
    parser.add_argument(
        "--parquet-dir",
        type=str,
        default="repositories.ghaw.csv",
        help="Directorio donde se encuentra repositories.parquet.",
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
        default="ghaw_only_repositories.parquet",
        help="Nombre del archivo Parquet de salida.",
    )

    args = parser.parse_args()

    transform_to_ghaw_only_parquet(
        input_csv=args.input_csv,
        parquet_dir=args.parquet_dir,
        repo_column=args.repo_column,
        output_file=args.output_file,
    )