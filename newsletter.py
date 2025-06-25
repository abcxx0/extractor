#!/usr/bin/env python3
import pandas as pd
import csv
from datetime import datetime, timedelta
import os
import sys

def detect_delimiter(path, sample_size=2048):
    with open(path, newline='', encoding='utf-8') as f:
        sample = f.read(sample_size)
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
            return dialect.delimiter
        except csv.Error:
            return ','  # fallback

def main(csv_path, out_dir):
    # 1) Detectar delimitador
    sep = detect_delimiter(csv_path)
    print(f"🕵️‍♀️ Delimitador detectado: '{sep}'")

    # 2) Leer CSV con motor python
    try:
        df = pd.read_csv(
            csv_path,
            sep=sep,
            engine='python',
            encoding='utf-8',
            on_bad_lines='warn'  # warnings para líneas malas
        )
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        sys.exit(1)

    # 3) Detectar columna de fecha
    cols = df.columns.tolist()
    date_col = next((c for c in cols if 'fecha' in c.lower()), None)
    if not date_col:
        print(f"❌ No se encontró columna de fecha en {cols}")
        sys.exit(1)

    # 4) Parsear fechas
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    if df[date_col].isna().all():
        print(f"❌ No se pudo parsear ninguna fecha en '{date_col}'")
        sys.exit(1)

    # 5) Filtrar últimos 7 días
    hoy = datetime.now()
    corte = hoy - timedelta(days=7)
    df7 = df[df[date_col] >= corte]

    # 6) Preparar salida
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{hoy.date()}-newsletter.md")

    # 7) Escribir Markdown
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(f"# Newsletter semanal ({hoy.date()})\n\n")
        for _, row in df7.iterrows():
            title = row.get('Título') or row.get('Titulo') or row.get('title') or 'Sin título'
            summary = row.get('Resumen') or row.get('resumen') or row.get('summary') or ''
            url = row.get('Url') or row.get('URL') or row.get('url') or ''
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
