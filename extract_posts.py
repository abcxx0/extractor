# 1) Imports
import requests, pandas as pd
from datetime import datetime
from requests.auth import HTTPBasicAuth

# 2) Credenciales y URL base
WP_USER = "redaccion"
WP_PASS = "redaccion"
BASE_API = "https://ciudadanocalamuchita.com.ar/wp-json/wp/v2"
auth     = HTTPBasicAuth(WP_USER, WP_PASS)

# 3) Define la fecha de corte
after_date = "2025-05-20T00:00:00"

# Debug: inicio
print("🔍 Iniciando extracción de posts...", flush=True)

# 4) Trae usuarios y construye el mapa de autores
try:
    resp_users = requests.get(f"{BASE_API}/users?per_page=100", auth=auth, timeout=10)
    resp_users.raise_for_status()
    users = resp_users.json()
    autor_map = { str(u["id"]): u["name"] for u in users }
    print(f"👥 {len(autor_map)} autores cargados.", flush=True)
except Exception as e:
    print("❌ Error al obtener autores:", e, flush=True)
    exit(1)

# 5) Paginación de posts
page = 1
all_posts = []
while True:
    print(f"📄 Obteniendo página {page}...", flush=True)
    try:
        resp = requests.get(
            f"{BASE_API}/posts?after={after_date}&per_page=100&page={page}",
            auth=auth,
            timeout=10
        )
        resp.raise_for_status()
        posts = resp.json()
    except Exception as e:
        print(f"❌ Error en página {page}:", e, flush=True)
        break

    if not posts:
        print("✅ No quedan posts. Terminando paginación.", flush=True)
        break

    all_posts.extend(posts)
    page += 1

print(f"🔢 Total de posts obtenidos: {len(all_posts)}", flush=True)

# 6) Construye DataFrame y guarda
rows = []
for p in all_posts:
    rows.append({
        "ID":     p["id"],
        "Fecha":  datetime.strptime(p["date"], "%Y-%m-%dT%H:%M:%S"),
        "Autor":  autor_map.get(str(p["author"]), p["author"]),
        "Título": p["title"]["rendered"],
        "URL":    p["link"]
    })

df = pd.DataFrame(rows)
output_file = "posts_extraidos.csv"
df.to_csv(output_file, index=False)
print(f"💾 Guardado en {output_file}", flush=True)
