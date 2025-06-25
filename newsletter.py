#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os, sys

def detect_delimiter(path):
    # fuerza punto y coma, o detecta automáticamente si prefieres
    return ';'

def main(csv_path, out_dir):
    # --- Carga y filtra ---
    sep = detect_delimiter(csv_path)
    df = pd.read_csv(csv_path, sep=sep, engine='python', encoding='utf-8', on_bad_lines='warn')
    df.columns = [c.strip() for c in df.columns]
    # detectar columna de fecha
    date_col = next((c for c in df.columns if 'fecha' in c.lower()), None)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    df7 = df[df[date_col] >= cutoff].copy()

    # --- Métricas generales ---
    total = len(df7)
    topicos = df7['Topico_Final'].fillna('Sin tópico')
    counts = topicos.value_counts()
    n_topics = counts.size
    top3 = counts.head(3)

    # --- Generación de gráfico ---
    os.makedirs(out_dir, exist_ok=True)
    chart_path = os.path.join(out_dir, 'bar_topics.png')
    plt.figure(figsize=(6,4))
    counts.plot.bar()
    plt.title('Artículos por tópico (últimos 7d)')
    plt.ylabel('Cantidad')
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

    # --- Selección de artículos destacados ---
    recent = df7.sort_values(date_col, ascending=False).head(3)

    # --- Montar Markdown completo ---
    md = []
    md.append(f"# Newsletter semanal ({datetime.now().date()})\n")
    md.append(f"- **Total de artículos:** {total}")
    md.append(f"- **Tópicos cubiertos:** {n_topics}\n")
    md.append("## Tópicos más frecuentes")
    for tema, cnt in top3.items():
        md.append(f"- **{tema}**: {cnt} notas")
    md.append("\n---\n")
    md.append("## Gráfico de distribución por tópico")
    md.append(f"![Artículos por tópico]({os.path.basename(chart_path)})\n")
    md.append("---\n")
    md.append("## Artículos destacados\n")
    for _, row in recent.iterrows():
        title   = row.get('Título', row.get('Titulo', 'Sin título'))
        summary = row.get('Resumen', '').strip()
        url     = row.get('Url', row.get('URL', ''))
        date    = row[date_col].date()
        md.append(f"### {title}  \n*{date}*  \n\n{summary}  \n\n[Leer más]({url})\n")

    # escribir Markdown
    md_file = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print(f"✅ Newsletter con análisis generada en {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python newsletter_analysis.py <csv_path> <out_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
