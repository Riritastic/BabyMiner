import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
from huggingface_hub import HfApi, create_repo


def upload_dataset_to_hf(
    dataset_dir: str = "dataset_parquet",
    repo_id: str = None,
    private: bool = False,
):
    """Carga variables desde .env y sube el directorio Parquet a Hugging Face Hub."""
    load_dotenv()

    # 1. Obtener credenciales y parámetros desde el entorno
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError(
            "❌ Error: 'HF_TOKEN' no está definido en el archivo .env"
        )

    target_repo_id = repo_id or os.getenv("HF_REPO_ID")
    if not target_repo_id:
        raise ValueError(
            "❌ Error: 'HF_REPO_ID' no está definido en el .env ni se pasó como argumento."
        )

    dataset_path = Path(dataset_dir)
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"❌ La carpeta de entrada '{dataset_dir}' no existe."
        )

    api = HfApi(token=token)

    # 2. Crear el repositorio en Hugging Face (si no existe)
    print(f"📦 Verificando/Creando repositorio en Hugging Face: {target_repo_id}...")
    create_repo(
        repo_id=target_repo_id,
        repo_type="dataset",
        private=private,
        exist_ok=True,
        token=token,
    )

    # 3. Subir la carpeta completa de Parquets
    print(f"🚀 Subiendo archivos desde '{dataset_path}' hacia '{target_repo_id}'...")
    api.upload_folder(
        folder_path=str(dataset_path),
        repo_id=target_repo_id,
        repo_type="dataset",
    )

    print("\n✅ Subida completada exitosamente.")
    print(f"🔗 Enlace al dataset: https://huggingface.co/datasets/{target_repo_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sube archivos Parquet a Hugging Face usando configuraciones del .env"
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="dataset_parquet",
        help="Directorio local con los archivos Parquet a subir.",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Define si el repositorio en Hugging Face debe ser privado.",
    )

    args = parser.parse_args()

    upload_dataset_to_hf(
        dataset_dir=args.dataset_dir,
        private=args.private,
    )