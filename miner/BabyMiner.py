import os
import time
import requests
import pandas as pd
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- CONFIGURACIÓN DE ARCHIVOS ---
INPUT_CSV = "results.csv"
ENRICHED_CSV = "results_con_clasificacion.csv"       # CSV temporal/enriquecido
FINAL_FILTERED_CSV = "repositorios_gh_aw_filtrados.csv" # CSV final entregable

REPO_COLUMN = 'name'      # Columna del CSV original que contiene 'usuario/repositorio'
BATCH_SIZE = 50           # Cantidad de elementos a procesar por bloque antes de guardar
MAX_WORKERS = 10          # Hilos simultáneos

# --- CARGA Y VALIDACIÓN DE TOKENS DESDE .ENV ---
# Lee la variable GITHUB_TOKENS separada por comas
tokens_env = os.getenv("GITHUB_TOKENS", "")
TOKENS = [token.strip() for token in tokens_env.split(",") if token.strip()]

# Si no hay tokens configurados en .env, intenta leer tokens individuales (p. ej. GITHUB_TOKEN_1, GITHUB_TOKEN_2)
if not TOKENS:
    fallback_tokens = [
        os.getenv("GITHUB_TOKEN_1"),
        os.getenv("GITHUB_TOKEN_2"),
        os.getenv("GITHUB_TOKEN_3"),
        os.getenv("GITHUB_TOKEN")
    ]
    TOKENS = [t.strip() for t in fallback_tokens if t and t.strip()]

if not TOKENS:
    raise ValueError(
       """No se encontraron tokens válidos en el archivo .env. "
        "Asegúrate de definir la variable GITHUB_TOKENS="token1,token2" en tu .env"""
    )

# Generador cíclico para alternar tokens (Round-Robin)
token_pool = cycle(TOKENS)

def get_next_headers():
    """Obtiene las cabeceras HTTP usando el siguiente token disponible."""
    token = next(token_pool)
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def check_gh_aw(repo_full_name):
    """
    Verifica si en el repositorio existe el par 'nombre.md' y 'nombre.lock.yml'
    dentro de .github/workflows/
    """
    url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows"
    
    while True:
        headers = get_next_headers()
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # Si un token supera el límite de cuota (403 o 429), reintenta inmediatamente con otro token
            if response.status_code in (403, 429):
                reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 60))
                sleep_duration = max(reset_time - int(time.time()), 5) + 1
                print(f"\n[ALERTA] Límite alcanzado en un token. Alternando al siguiente...")
                time.sleep(1)
                continue
                
            # Si el directorio no existe (404) o hay algún error de acceso
            if response.status_code != 200:
                return (repo_full_name, 0)
                
            items = response.json()
            if not isinstance(items, list):
                return (repo_full_name, 0)
            
            filenames = {item['name'] for item in items if item.get('type') == 'file'}
            
            # Filtrar los nombres base de archivos Markdown (.md)
            md_bases = {f[:-3] for f in filenames if f.endswith('.md')}
            
            # Comprobar si existe el archivo .lock.yml coincidente
            for base_name in md_bases:
                if f"{base_name}.lock.yml" in filenames:
                    return (repo_full_name, 1)
                    
            return (repo_full_name, 0)

        except Exception as e:
            print(f"Error procesando {repo_full_name}: {e}")
            return (repo_full_name, 0)

def main():
    print(f"Iniciando ejecutor con {len(TOKENS)} token(s) de GitHub desde el entorno.")
    
    df_original = pd.read_csv(INPUT_CSV)
    
    # Reanudar desde avance previo si existe el archivo enriquecido
    if os.path.exists(ENRICHED_CSV):
        print("Se encontró un archivo procesado previamente. Cargando avance...")
        df_processed = pd.read_csv(ENRICHED_CSV)
    else:
        df_processed = df_original.copy()
        df_processed['uses_gh_aw'] = None

    # Filtrar solo las filas pendientes por evaluar
    pending_mask = df_processed['uses_gh_aw'].isna()
    pending_indices = df_processed[pending_mask].index.tolist()
    total_pending = len(pending_indices)

    print(f"Total de repositorios pendientes por evaluar: {total_pending} de {len(df_processed)}")

    # Procesar en bloques (batches)
    for i in range(0, total_pending, BATCH_SIZE):
        batch_indices = pending_indices[i:i + BATCH_SIZE]
        batch_repos = df_processed.loc[batch_indices, REPO_COLUMN].tolist()
        
        results = {}
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(check_gh_aw, repo) for repo in batch_repos]
            for future in as_completed(futures):
                repo_name, status = future.result()
                results[repo_name] = status

        # Actualizar datos en el DataFrame principal
        for idx in batch_indices:
            repo_name = df_processed.loc[idx, REPO_COLUMN]
            df_processed.loc[idx, 'uses_gh_aw'] = results.get(repo_name, 0)

        # GUARDADO INMEDIATO EN DISCO
        df_processed.to_csv(ENRICHED_CSV, index=False)
        
        processed_so_far = min(i + BATCH_SIZE, total_pending)
        print(f"Progreso: {processed_so_far}/{total_pending} repositorios analizados y guardados.")

    # Asegurar que la columna binaria sea un entero
    df_processed['uses_gh_aw'] = df_processed['uses_gh_aw'].astype(int)
    
    # Exportar el CSV filtrado listo para entregar (solo con uses_gh_aw == 1)
    df_filtered = df_processed[df_processed['uses_gh_aw'] == 1].copy()
    df_filtered.to_csv(FINAL_FILTERED_CSV, index=False)

    print("\n--- PROCESO FINALIZADO CON ÉXITO ---")
    print(f"Total analizados: {len(df_processed)}")
    print(f"Repositorios que usan GH-AW: {len(df_filtered)}")
    print(f"1. Dataset enriquecido generado: {ENRICHED_CSV}")
    print(f"2. CSV final entregable: {FINAL_FILTERED_CSV}")

if __name__ == "__main__":
    main()