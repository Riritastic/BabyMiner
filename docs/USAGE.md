#### `docs/USAGE.md`
```markdown
# Instrucciones de Uso

### Generar Dataset Parquet
```
```bash
Ejecuta el siguiente comando especificando el archivo CSV de candidatos y el directorio donde se crearán las tablas en formato Apache Parquet:
```
```bash
#Formato para utilizar todas las tokens
miner --input-csv repos.csv --output-dir dataset_parquet --workers 15
```
```bash
#Formato para utilizar tokens especifica
miner --input-csv repos.csv --output-dir dataset_parquet --workers 15 --max-tokens 2
```