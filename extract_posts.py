# 1) Instala dependencias (solo la primera vez)

# 2) Imports
import requests, pandas as pd
from datetime import datetime
from requests.auth import HTTPBasicAuth

# 3) Credenciales y URL base
WP_USER  = "redaccion"
WP_PASS  = "redaccion"
BASE_API = "https://ciudadanocalamuchita.com.ar/wp-json/wp/v2"
auth     = HTTPBasicAuth(WP_USER, WP_PASS)

# 4) Define la fecha de corte manualmente
after_date = "2025-05-20T00:00:00"

# 5) Paginación segura sin raise_for_status()
posts, page = [], 1
while True:
    resp = requests.get(
        f"{BASE_API}/posts",
        params={
            "per_page": 100,
            "page": page,
            "after": after_date,
            "_fields": "id,title,author,categories,date,views"
        },
        auth=auth,
        timeout=10
    )
    if resp.status_code != 200:  # rompe al final de páginas
        break
    data = resp.json()
    if not data:                # también rompe si llega un array vacío
        break

    posts.extend(data)
    page += 1
# 6) Procesar los resultados en un DataFrame (con mapeo de autor y categorías)
rows = []
for p in posts:
    dt = datetime.strptime(p['date'], "%Y-%m-%dT%H:%M:%S")
    rows.append({
        "ID": p['id'],
        "Título": p['title']['rendered'],
        "Autor": autor_map.get(p['author'], f"Autor-{p['author']}"),
        "Categorías": ", ".join(cat_map.get(cid, f"Categoría-{cid}") for cid in p['categories']),
        "Fecha": dt.strftime("%Y-%m-%d"),
        "Hora": dt.strftime("%H:%M:%S"),
        "Vistas": p.get('views', 0),
        "Topico_Final": ""  # tu función de clasificación acá
    })
df = pd.DataFrame(rows)

df.head()
