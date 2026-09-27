#### `docs/USAGE.md`

# Instrucciones de Uso

## 🚀 Ejecución de la Extracción de Datos (Data Miner)

Antes de ejecutar los notebooks de Análisis Exploratorio de Datos (EDA), es necesario correr el extractor para generar las 5 tablas Parquet con el esquema relacional actualizado.

### 1. Variables de Entorno

Asegúrate de contar con uno o más tokens de GitHub en un archivo `.env` o en tus variables del sistema para evitar límites de tasa (rate limits) durante el escaneo:

```bash
# Crear/editar el archivo .env en la raíz del proyecto
GH_TOKENS="ghp_token1,ghp_token2,ghp_token3" #ejemplo
```
### 2. Comandos de Ejecución


```bash
python -m miner.main --input data/candidates.csv --output data/raw/ --batch-size 50 --workers 15
```
