#!/usr/bin/env python3
import pandas as pd
from datetime import datetime, timedelta
import os, sys

def main(csv_path, out_dir):
    df = pd.read_csv(csv_path, sep=';', parse_dates=['Fecha'])
    hoy = datetime.now()
    df7 = df[df['Fecha'] >= hoy - timedelta(days=7)]

    os.makedirs(out_dir, exist_ok=True)
    path_out = os.path.join(out_dir, f"{hoy.date()}-newsletter.md")

    with open(path_out, 'w', encoding='utf-8') as f:
        f.write(f"# Newsletter semanal ({hoy.date()})\n\n")
        for _, row in df7.iterrows():
            f.write(f"## {row['Título']}\n{row['Resumen']}\n[Leer más]({row['Url']})\n\n")

    print("✅ Newsletter generada en", path_out)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
