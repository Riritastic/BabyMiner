# Tarea 4: Análisis Exploratorio de Datos (EDA) - GitHub Agentic Workflows

Este directorio contiene el Análisis Exploratorio de Datos (EDA) sobre el dataset de GitHub Agentic Workflows extraído mediante **Miner**.

## 🔗 Enlaces a Datos
* **Dataset Publicado (Hugging Face):** [ENLACE_A_TU_DATASET_EN_HUGGINGFACE]
* **Estructura del Dataset:**
  * `repositories.parquet`: Repositorios con GH-AW.
  * `workflows.parquet`: Metadatos del frontmatter.
  * `workflow_bodies.parquet`: Contenido Markdown de los workflows.

## 📁 Ubicación de Archivos de Datos
Para ejecutar los notebooks localmente, coloca los archivos Parquet en las siguientes rutas dentro de `eda/`:
* `eda/data/raw/repositories.parquet`
* `eda/data/raw/workflows.parquet`
* `eda/data/raw/workflow_bodies.parquet`

Los notebooks generarán automáticamente los datos procesados en `eda/data/processed/`.

## 🛠️ Instalación y Configuración del Entorno

1. **Activar el entorno virtual del proyecto:**
   ```bash
   # En Windows:
   .venv\Scripts\activate
   # En Linux/macOS:
   source .venv/bin/activate
    ```
2. **Instalar dependencias necesarias:**
    
    Dependencias basicas
    ```bash
    pip install jupyterlab ipykernel pandas pyarrow matplotlib seaborn
    Registrar el Kernel de Jupyter:
    ```

    Miner
    ```bash
    python -m ipykernel install --user --name=miner-env --display-name "Python (miner-env)"
    Iniciar JupyterLab:
    ```
    
3. **Iniciar jupyter lab:**    
    ```bash
    jupyter lab
    ```




    tablas body + md + yml + Repo (nombre, dueño, last commit,) 