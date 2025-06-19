print("🚀 Arrancando extract_posts.py...", flush=True)

import pandas as pd
import requests
from tqdm import tqdm
import base64
from datetime import datetime
import os

# Configuración
BASE_URL     = "https://ciudadanocalamuchita.com.ar/wp-json/wp/v2"
CREDENTIALS  = base64.b64encode(b"redaccion:redaccion").decode()
HEADERS      = {"Authorization": f"Basic {CREDENTIALS}"}
ARCHIVO_CSV  = "datos_actualizados.csv"
COLUMNAS     = ['ID', 'Título', 'Autor', 'Categorías', 'Fecha', 'Hora', 'Vistas', 'Topico_Final']

# Leer última fecha guardada si existe, o usar una vieja por defecto
if os.path.exists("ultima_fecha.txt"):
    with open("ultima_fecha.txt", "r") as f:
        fecha_str = f.read().strip()
        AFTER_DATE = f"{fecha_str}T00:00:00"
else:
    AFTER_DATE = "2024-12-01T00:00:00"  # una fecha vieja si es la primera vez


def inicializar_csv():
    if not os.path.exists(ARCHIVO_CSV):
        pd.DataFrame(columns=COLUMNAS).to_csv(ARCHIVO_CSV, index=False, sep=';')

def cargar_datos_existentes():
    try:
        df = pd.read_csv(ARCHIVO_CSV, sep=';')
        df['Fecha'] = df['Fecha'].astype(str)
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=COLUMNAS)

def obtener_ultimo_id():
    df = cargar_datos_existentes()
    return df['ID'].max() if not df.empty else 0

def obtener_mapeos():
    print("Obteniendo mapeos de autores y categorías...", flush=True)
    autores     = requests.get(f"{BASE_URL}/users?per_page=100", headers=HEADERS, timeout=10).json()
    categorias  = requests.get(f"{BASE_URL}/categories?per_page=100", headers=HEADERS, timeout=10).json()
    autores_map     = {a['id']: a.get('name', f"Autor-{a['id']}") for a in autores}
    categorias_map  = {c['id']: c.get('name', f"Categoría-{c['id']}") for c in categorias}
    return autores_map, categorias_map

def obtener_nuevos_posts(ultimo_id):
    print("\nBuscando nuevos artículos...", flush=True)
    nuevos_posts = []
    page = 1
    with tqdm(desc="Progreso páginas") as pbar:
        while True:
            resp = requests.get(
                f"{BASE_URL}/posts",
                params={
                    "page": page,
                    "per_page": 100,
                    "orderby": "id",
                    "order": "asc",
                    "_fields": "id,title,author,categories,date,views",  # <- Añadido views
                    "after": AFTER_DATE
                },
                headers=HEADERS,
                timeout=10
            )
            if resp.status_code != 200:
                print(f"❌ Error HTTP {resp.status_code} en página {page}", flush=True)
                break
            posts = resp.json()
            if not posts:
                break
            filtrados = [p for p in posts if p['id'] > ultimo_id]
            if not filtrados:
                break
            nuevos_posts.extend(filtrados)
            page += 1
            pbar.update(1)
    return nuevos_posts

def procesar_posts(posts, autores_map, categorias_map):
    print(f"\nProcesando {len(posts)} artículos...", flush=True)
    datos = []
    for p in tqdm(posts, desc="Procesando artículos"):
        fecha = datetime.strptime(p['date'], "%Y-%m-%dT%H:%M:%S")
        datos.append({
            "ID":            p['id'],
            "Título":        p['title']['rendered'],
            "Autor":         autores_map.get(p['author'], f"Autor-{p['author']}"),
            "Categorías":    ", ".join(categorias_map.get(cid, f"Categoría-{cid}") for cid in p.get('categories', [])),
            "Fecha":         fecha.strftime("%Y-%m-%d"),
            "Hora":          fecha.strftime("%H:%M:%S"),
            "Vistas":        p.get('views', 0),  # <- Usamos el campo views
            "Topico_Final":  ""
        })
    return datos

def actualizar_csv(nuevos_datos):
    df_old = cargar_datos_existentes()
    df_new = pd.DataFrame(nuevos_datos)
    df_final = pd.concat([df_old, df_new]).drop_duplicates('ID')
    df_final = df_final.sort_values(['Fecha','Hora'], ascending=[False, False])
    df_final.to_csv(ARCHIVO_CSV, index=False, sep=';')
    return len(df_new)

def main():
    inicializar_csv()
    ultimo_id     = obtener_ultimo_id()
    autores_map, categorias_map = obtener_mapeos()
    nuevos_posts  = obtener_nuevos_posts(ultimo_id)

    # --- Procesar y guardar resultados -------------------------------
    # Procesamos SIEMPRE, aunque nuevos_posts esté vacío.
    nuevos_datos = procesar_posts(nuevos_posts, autores_map, categorias_map)
    cnt = actualizar_csv(nuevos_datos)
    print(f"\n✅ Se agregaron {cnt} registros a {ARCHIVO_CSV}", flush=True)

    # Guardar la última fecha para evitar duplicados (solo si hubo datos)
    if nuevos_datos:
        ultima_fecha = max(d["Fecha"] for d in nuevos_datos)
        with open("ultima_fecha.txt", "w") as f:
            f.write(ultima_fecha)

if __name__ == "__main__":
    main()




