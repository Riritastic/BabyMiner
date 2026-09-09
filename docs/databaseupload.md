huggingface-cli login
from huggingface_hub import HfApi

api = HfApi()
api.upload_folder(
    folder_path="./dist_parquet",
    repo_id="tu-usuario/gh-agentic-workflows-dataset",
    repo_type="dataset",
)

python upload_hf.py --dataset-dir eda/data/processed