#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os, sys, csv

def load_and_detect(csv_path):
    # Lee con punto y coma y motor python
    df = pd.read_csv(csv_path, sep=';', engine='python',
                     on_bad_lines='warn', encoding='utf-8')
    df.columns = df.columns.str.strip()
    cols = list(df.columns)
    # Detecta columnas clave
    date_col = next((c for c in cols if 'fecha' in c.lower()), None)
    topic_col = next((c for c in cols if 'topico' in c.lower() or 'tópico' in c.lower()), None)
    title_col = next((c for c in cols if 'títul' in c.lower() or 'titulo' in c.lower()), None)
    summary_col = next((c for c in cols if 'resumen' in c.lower()), None)
    url_col = next((c for c in cols if 'url' in c.lower()), None)
    # Verifica detección
    missing = [name for name,var in [
        ('Fecha', date_col), ('Tópico', topic_col),
        ('Título', title_col), ('Resumen', summary_col),
        ('URL', url_col)] if var is None]
    if missing:
        print(f"❌ No pude detectar columnas: {missing}")
        print("Columnas encontradas:", cols)
        sys.exit(1)
    return df, date_col, topic_col, title_col, summary_col, url_col

def update_history(hist_path, total):
    today = datetime.now().date()
    if os.path.exists(hist_path):
        hist = pd.read_csv(hist_path, parse_dates=['fecha'])
    else:
        hist = pd.DataFrame(columns=['fecha','total'])
    prev = hist[hist['fecha'] == (today - timedelta(days=7))]
    # Añade registro
    hist = pd.concat([hist, pd.DataFrame([{'fecha': today, 'total': total}])], ignore_index=True)
    hist.to_csv(hist_path, index=False)
    return prev

def compute_trends(df_curr, df_prev, topic_col):
    curr = df_curr[topic_col].value_counts().rename('current')
    prev = df_prev[topic_col].value_counts().rename('previous')
    trend = pd.concat([prev, curr], axis=1).fillna(0)
    trend['delta'] = trend['current'] - trend['previous']
    trend['pct_change'] = trend['delta'] / trend['previous'].replace(0,1) * 100
    trend['engagement'] = df_curr.groupby(topic_col)['Vistas'].sum() / trend['current']
    return trend

def main(csv_path, out_dir):
    df, date_col, topic_col, title_col, summary_col, url_col = load_and_detect(csv_path)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    df7 = df[df[date_col] >= cutoff].copy()
    total = len(df7)

    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    df_prev = update_history(hist_path, total)

    trend = compute_trends(df7, df_prev, topic_col) if not df_prev.empty else None

    # Gráfico
    chart = os.path.join(out_dir, 'bar_topics.png')
    df7[topic_col].value_counts().plot.bar()
    plt.title('Artículos por tópico (últimos 7d)')
    plt.tight_layout(); plt.savefig(chart); plt.close()

    # Construye narrativa
    md = [f"# Newsletter semanal ({datetime.now().date()})\n",
          f"- **Total de artículos:** {total}"]
    if trend is not None:
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
        md.append(f"### {r[title_col]}\n*{date}*\n\n{r[summary_col]}\n\n[Leer más]({r[url_col]})\n")

    out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Uso: python newsletter.py <csv> <out>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
