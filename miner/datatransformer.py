import argparse
from pathlib import Path
import pandas as pd


def parquet_to_csv(
    parquet_dir: str = "repositories.ghaw.csv",
    parquet_file: str = "repositories.parquet",
    output_csv: str = "repositories_ghaw_positives.csv",
) -> Path:
    """Lee el Parquet de casos positivos de GH-AW y lo exporta como un archivo CSV."""
    p_dir = Path(parquet_dir)
    parquet_path = p_dir / parquet_file

    if not parquet_path.exists():
        raise FileNotFoundError(
            f"❌ No se encontró el archivo Parquet en: {parquet_path}"
        )

    print(f"📖 Leyendo dataset de casos positivos desde: {parquet_path}...")
    df_positives = pd.read_parquet(parquet_path)

    destination_path = p_dir / output_csv
    print(f"💾 Convirtiendo y guardando en CSV: {destination_path}...")
    df_positives.to_csv(destination_path, index=False)

    print("\n✅ Conversión completada exitosamente.")
    print(
        f"  - Repositorios positivos exportados: {len(df_positives):,} filas"
    )
    print(f"  - Archivo generado: {destination_path}")

    return destination_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convierte el Parquet de casos positivos de GH-AW a formato CSV."
    )
    parser.add_argument(
        "--parquet-dir",
        type=str,
        default="repositories.ghaw.csv",
        help="Directorio donde se encuentra el Parquet.",
    )
    parser.add_argument(
        "--parquet-file",
        type=str,
        default="repositories.parquet",
        help="Nombre del archivo Parquet de origen.",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="repositories_ghaw_positives.csv",
        help="Nombre del CSV de salida.",
    )

    args = parser.parse_args()

    parquet_to_csv(
        parquet_dir=args.parquet_dir,
        parquet_file=args.parquet_file,
        output_csv=args.output_csv,
    )
    #python -m miner.datatransformer