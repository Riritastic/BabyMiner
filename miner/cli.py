import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

from miner.client import GitHubClient
from miner.processor import DatasetProcessor


def get_tokens_from_env(max_requested: int = None) -> list[str]:
    """Carga los tokens desde el entorno o archivo .env.

    Soporta GITHUB_TOKENS (separados por coma) o GITHUB_TOKEN_1, GITHUB_TOKEN_2,
    etc.
    """
    # Cargar variables desde el archivo .env si existe
    load_dotenv()

    tokens = []

    # 1. Intentar cargar desde GITHUB_TOKENS (separados por coma)
    raw_tokens = os.getenv("GITHUB_TOKENS", "")
    if raw_tokens:
        tokens.extend([t.strip() for t in raw_tokens.split(",") if t.strip()])

    # 2. Intentar cargar variables individuales GITHUB_TOKEN / GITHUB_TOKEN_1 / GITHUB_TOKEN_2...
    if not tokens:
        single_token = os.getenv("GITHUB_TOKEN")
        if single_token:
            tokens.append(single_token.strip())

        i = 1
        while True:
            t = os.getenv(f"GITHUB_TOKEN_{i}")
            if not t:
                break
            tokens.append(t.strip())
            i += 1

    # Eliminar duplicados manteniendo el orden
    unique_tokens = list(dict.fromkeys(tokens))

    if not unique_tokens:
        return []

    # Ajustar a la cantidad solicitada (o al máximo disponible por defecto)
    if max_requested is not None and max_requested > 0:
        if max_requested < len(unique_tokens):
            print(
                f"ℹ️ Usando {max_requested} token(s) de los {len(unique_tokens)} disponibles en .env."
            )
            return unique_tokens[:max_requested]
        elif max_requested > len(unique_tokens):
            print(
                f"⚠️ Se solicitaron {max_requested} tokens, pero solo hay {len(unique_tokens)} en el .env."
            )
            print(f"ℹ️ Se usará el máximo disponible: {len(unique_tokens)} token(s).")

    return unique_tokens


def main():
    parser = argparse.ArgumentParser(
        description="Miner de Workflows GH-AW para repositorios de GitHub."
    )
    parser.add_argument(
        "--input-csv",
        type=str,
        required=True,
        help="Ruta al archivo CSV con la lista de repositorios.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="dataset_parquet",
        help="Directorio de salida para los archivos Parquet.",
    )
    parser.add_argument(
        "--repo-column",
        type=str,
        default="name",
        help="Nombre de la columna en el CSV que contiene el formato owner/repo.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=15,
        help="Número de hilos concurrentes para procesamiento en paralelo.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Cantidad máxima de tokens a utilizar desde el .env (por defecto usa todos los disponibles).",
    )

    args = parser.parse_args()

    # Obtener tokens desde el archivo .env
    tokens = get_tokens_from_env(max_requested=args.max_tokens)

    if not tokens:
        print("❌ Error: No se encontraron tokens de GitHub en el archivo .env ni en las variables de entorno.")
        print(" Asegúrate de definir GITHUB_TOKENS o GITHUB_TOKEN_1 en tu archivo .env.")
        return

    # Instanciar el cliente con los tokens cargados automáticamente
    client = GitHubClient(tokens=tokens)

    processor = DatasetProcessor(
        client=client,
        repo_column=args.repo_column,
        max_workers=args.workers
    )

    print(
        f"🚀 Iniciando minería con {len(tokens)} token(s) en paralelo y {args.workers} workers..."
    )

    results = processor.process_and_export_parquet(
        input_csv=args.input_csv,
        output_dir=Path(args.output_dir)
    )

    print("\n Process completado exitosamente.")
    print(f"  - Repositorios GH-AW encontrados: {results['repositories']}")
    print(f"  - Metadatos de Workflows: {results['workflows']}")
    print(f"  - Cuerpos de Workflows: {results['bodies']}")


if __name__ == "__main__":
    main()