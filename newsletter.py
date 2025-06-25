#!/usr/bin/env python3
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

def main(csv_path, out_dir):
    # 1) Lee el CSV sin parsear fechas
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8')

    # 2) Detecta la columna de fecha (cualquier nombre que contenga 'fecha')
    cols = df.columns.tolist()
    date_col = next((c for c in cols if 'fecha' in c.lower()), None)
    if date_col is None:
        raise ValueError(f"No se encontró ninguna columna de fecha en {cols}")
    
    # 3) Parsear esa columna a datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    if df[date_col].isna().all():
        raise ValueError(f"No se pudo parsear ninguna fecha en la columna '{date_col}'")

    # 4) Filtrar los últimos 7 días
    hoy = datetime.now()
    hace_7 = hoy - timedelta(days=7)
    df7 = df[df[date_col] >= hace_7]

    # 5) Preparar el directorio de salida
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{hoy.date()}-newsletter.md")

    # 6) Escribir el Markdown
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"# Newsletter semanal ({hoy.date()})\n\n")
        for _, row in df7.iterrows():
            title = row.get('Título') or row.get('Titulo') or row.get('title', 'Sin título')
            summary = row.get('Resumen') or row.get('resumen') or row.get('summary', '')
            url = row.get('Url') or row.get('URL') or row.get('url', '')
            f.write(f"## {title}\n\n")
            f.write(f"{summary}\n\n")
            if url:
                f.write(f"[Leer más]({url})\n\n")
    print(f"✅ Newsletter generada en {out_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python newsletter.py <ruta_csv> <directorio_salida>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
