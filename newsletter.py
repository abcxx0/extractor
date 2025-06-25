#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os, sys

def detect_delimiter(path): return ';'

def load_and_filter(csv_path):
    sep = detect_delimiter(csv_path)
    df = pd.read_csv(csv_path, sep=sep, engine='python', on_bad_lines='warn', encoding='utf-8')
    df.columns = df.columns.str.strip()
    date_col = next((c for c in df.columns if 'fecha' in c.lower()), None)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    return df[df[date_col] >= cutoff].copy(), date_col

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

def compute_trends(df_curr, df_prev):
    curr = df_curr['Topico_Final'].value_counts().rename('current')
    prev = df_prev['Topico_Final'].value_counts().rename('previous')
    trend = pd.concat([prev, curr], axis=1).fillna(0)
    trend['delta'] = trend['current'] - trend['previous']
    trend['pct_change'] = trend['delta'] / trend['previous'].replace(0, 1) * 100
    trend['engagement'] = df_curr.groupby('Topico_Final')['Vistas'].sum() / trend['current']
    return trend

def main(csv_path, out_dir):
    df7, date_col = load_and_filter(csv_path)
    total = len(df7)

    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    df_prev = update_history(hist_path, total)

    # Solo si hay datos de la semana previa
    trend = compute_trends(df7, df_prev) if not df_prev.empty else None

    # Gráfico de frecuencia
    chart = os.path.join(out_dir, 'bar_topics.png')
    df7['Topico_Final'].value_counts().plot.bar()
    plt.title('Artículos por tópico (últimos 7d)')
    plt.tight_layout(); plt.savefig(chart); plt.close()

    # Armar narrativa
    md = [f"# Newsletter semanal ({datetime.now().date()})\n",
          f"- **Total de artículos:** {total}"]
    if trend is not None:
        prev_total = int(df_prev['total'].iloc[0])
        pct = (total - prev_total) / prev_total * 100
        sign = "+" if pct >= 0 else ""
        md.append(f"- **Variación semanal:** {sign}{pct:.1f}% (de {prev_total} a {total} artículos)")
        # Top ganancia/pérdida
        gain = trend.sort_values('pct_change', ascending=False).iloc[0]
        loss = trend.sort_values('pct_change').iloc[0]
        md.append(f"- **Mayor incremento:** {gain.name} (+{gain['pct_change']:.0f}% notas)")
        md.append(f"- **Mayor disminución:** {loss.name} ({loss['pct_change']:.0f}% notas)")

    md += ["\n---\n", "## Distribución por tópico",
           f"![Artículos por tópico]({os.path.basename(chart)})",
           "\n---\n", "## Artículos destacados\n"]
    for _, r in df7.sort_values(date_col, ascending=False).head(3).iterrows():
        title, summary, url = r['Título'], r.get('Resumen',''), r.get('Url','')
        date = r[date_col].date()
        md.append(f"### {title}\n*{date}*\n\n{summary}\n\n[Leer más]({url})\n")

    out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))
    print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Uso: python newsletter.py <csv> <out>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
