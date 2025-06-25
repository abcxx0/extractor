#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os, sys, csv

def detect_delimiter(path, sample_size=2048):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        sample = f.read(sample_size)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[',',';','\t'])
        return dialect.delimiter
    except csv.Error:
        return ','

def load_and_detect(csv_path):
    sep = detect_delimiter(csv_path)
    print(f"🕵️‍♀️ Delimitador detectado: '{sep}'")
    df = pd.read_csv(csv_path, sep=sep, engine='python',
                     on_bad_lines='warn', encoding='utf-8')
    df.columns = df.columns.str.strip()
    cols = list(df.columns)
    # Detecta columnas
    date_col    = next((c for c in cols if 'fecha' in c.lower()), None)
    topic_col   = next((c for c in cols if 'topico' in c.lower()), None)
    title_col   = next((c for c in cols if 'títul' in c.lower() or 'titulo' in c.lower()), None)
    views_col   = next((c for c in cols if 'vistas' in c.lower()), None)
    # Opcionales
    summary_col = next((c for c in cols if 'resumen' in c.lower()), None)
    url_col     = next((c for c in cols if 'url' in c.lower()), None)

    # Columnas mínimas obligatorias
    missing = [n for n,v in [('Fecha',date_col),('Tópico',topic_col),
                             ('Título',title_col),('Vistas',views_col)] if v is None]
    if missing:
        print(f"❌ No pude detectar columnas obligatorias: {missing}")
        print("Columnas encontradas:", cols)
        sys.exit(1)

    return df, date_col, topic_col, title_col, summary_col, url_col, views_col

def update_history(hist_path, total):
    today = datetime.now().date()
    if os.path.exists(hist_path):
        hist = pd.read_csv(hist_path, parse_dates=['fecha'])
    else:
        hist = pd.DataFrame(columns=['fecha','total'])
    prev = hist[hist['fecha'] == (today - timedelta(days=7))]
    hist = pd.concat([hist, pd.DataFrame([{'fecha': today, 'total': total}])], ignore_index=True)
    hist.to_csv(hist_path, index=False)
    return prev

def compute_trends(df_curr, df_prev, topic_col, views_col):
    curr = df_curr[topic_col].value_counts().rename('current')
    prev = df_prev[topic_col].value_counts().rename('previous')
    trend = pd.concat([prev, curr], axis=1).fillna(0)
    trend['delta'] = trend['current'] - trend['previous']
    trend['pct_change'] = trend['delta'] / trend['previous'].replace(0,1) * 100
    trend['engagement'] = df_curr.groupby(topic_col)[views_col].sum() / trend['current']
    return trend

def main(csv_path, out_dir):
    df, date_col, topic_col, title_col, summary_col, url_col, views_col = load_and_detect(csv_path)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    df7 = df[df[date_col] >= cutoff].copy()
    total = len(df7)

    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    df_prev = update_history(hist_path, total)

    trend = compute_trends(df7, df_prev, topic_col, views_col) if not df_prev.empty else None

    # Gráfico de frecuencia
    chart = os.path.join(out_dir, 'bar_topics.png')
    df7[topic_col].value_counts().plot.bar()
    plt.title('Artículos por tópico (últimos 7d)')
    plt.tight_layout(); plt.savefig(chart); plt.close()

    # Construye narrativa
    md = [f"# Newsletter semanal ({datetime.now().date()})\n",
          f"- **Total de artículos:** {total}"]

    if trend is not None and not df_prev.empty:
        prev_total = int(df_prev['total'].iloc[0])
        pct = (total - prev_total) / prev_total * 100
        sign = "+" if pct>=0 else ""
        md.append(f"- **Variación semanal:** {sign}{pct:.1f}% (de {prev_total} a {total})")
        gain = trend.sort_values('pct_change', ascending=False).iloc[0]
        loss = trend.sort_values('pct_change').iloc[0]
        md.append(f"- **Mayor incremento:** {gain.name} (+{gain['pct_change']:.0f}% notas)")
        md.append(f"- **Mayor disminución:** {loss.name} ({loss['pct_change']:.0f}% notas)")

    md += ["\n---\n", "## Distribución por tópico",
           f"![Artículos por tópico]({os.path.basename(chart)})", "\n---\n", "## Artículos destacados\n"]

    for _, r in df7.sort_values(date_col, ascending=False).head(3).iterrows():
        date = r[date_col].date()
        linea = f"### {r[title_col]}\n*{date}*\n\n"
        if summary_col: linea += f"{r[summary_col]}\n\n"
        if url_col:     linea += f"[Leer más]({r[url_col]})\n"
        md.append(linea)

    out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Uso: python newsletter.py <csv> <out>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
