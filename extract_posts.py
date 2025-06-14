# 1) Imports
import requests, pandas as pd
from datetime import datetime
from requests.auth import HTTPBasicAuth

# 2) Credenciales y URL base
WP_USER = "redaccion"
WP_PASS = "redaccion"
BASE_API = "https://ciudadanocalamuchita.com.ar/wp-json/wp/v2"
auth     = HTTPBasicAuth(WP_USER, WP_PASS)

# 3) Define la fecha de corte manualmente
after_date = "2025-05-20T00:00:00"

# 4) Construye el mapeo de IDs de autor → nombre
users = requests.get(f"{BASE_API}/users?per_page=100", auth=auth).json()
autor_map = { str(u["id"]): u["name"] for u in users }

# 5) Extrae todos los posts paginando
page = 1
all_posts = []
while True:
    resp = requests.get(
        f"{BASE_API}/posts?after={after_date}&per_page=100&page={page}",
        auth=auth
    )
    posts = resp.json()
    if not posts:
        break
    all_posts.extend(posts)
    page += 1

# 6) Construye la lista de diccionarios
rows = []
for p in all_posts:
    rows.append({
        "ID":        p["id"],
        "Fecha":     datetime.strptime(p["date"], "%Y-%m-%dT%H:%M:%S"),
        "Autor":     autor_map.get(str(p["author"]), p["author"]),
        "Título":    p["title"]["rendered"],
        "URL":       p["link"]
    })

# 7) Guarda en CSV
df = pd.DataFrame(rows)
output_file = "posts_extraidos.csv"
df.to_csv(output_file, index=False)
print(f"Guardado en {output_file}")
