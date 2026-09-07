# BabyMiner

**BabyMiner** es una aplicación en línea de comandos (CLI) desarrollada en Python que permite identificar automáticamente si un conjunto de repositorios candidatos de GitHub utilizan **GitHub Agentic Workflows (GH-AW)**.

Un repositorio utiliza GH-AW si en el directorio `.github/workflows/` contiene al menos un par de archivos compuestos por un archivo Markdown (`.md`) y su equivalente compilado (`.lock.yml`) compartiendo el mismo nombre base (por ejemplo, `report.md` y `report.lock.yml`).

---

## Requisitos previos e Instalación

### 1. Clonar el repositorio
```bash
git clone [https://github.com/Riritastic/BabyMiner](https://github.com/Riritastic/BabyMiner)
cd miner
```
### 2. Instalación de ambiente .venv
```bash
python -m venv .venv
pip install -e .[dev]
```



### 3. Utilización de miner
```bash
Comando: miner repositorios.csv --output repositorios_ghaw.csv
Parámetros opcionales:
--output / -o: Ruta del archivo CSV resultado (Por defecto: repositorios_ghaw.csv).

--column / -c: Nombre de la columna en el CSV original que contiene el identificador usuario/repositorio (Por defecto: name).

--workers / -w: Cantidad de hilos en paralelo (Por defecto: 10)
```