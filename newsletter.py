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

    # Columnas obligatorias
    date_col  = next((c for c in cols if 'fecha' in c.lower()), None)
    topic_col = next((c for c in cols if 'topico' in c.lower()), None)
    title_col = next((c for c in cols if 'títul' in c.lower() or 'titulo' in c.lower()), None)
    views_col = next((c for c in cols if 'vistas' in c.lower()), None)

    missing = [n for n,v in [('Fecha',date_col),('Tópico',topic_col),
                             ('Título',title_col),('Vistas',views_col)] if v is None]
    if missing:
        print(f"❌ Faltan columnas obligatorias: {missing}")
        print("Columnas encontradas:", cols)
        sys.exit(1)

    # Opcionales
    summary_col = next((c for c in cols if 'resumen' in c.lower()), None)
    url_col     = next((c for c in cols if 'url' in c.lower()), None)

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
    trend['delta']      = trend['current'] - trend['previous']
    trend['pct_change'] = trend['delta'] / trend['previous'].replace(0,1) * 100
    trend['engagement'] = df_curr.groupby(topic_col)[views_col].sum() / trend['current']
    return trend

def main(csv_path, out_dir):
    # 1) Carga y detección de columnas
    df, date_col, topic_col, title_col, summary_col, url_col, views_col = load_and_detect(csv_path)

    # 2) Filtrado últimos 7 días
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    cutoff = datetime.now() - timedelta(days=7)
    df7 = df[df[date_col] >= cutoff].copy()
    total = len(df7)

    # 3) Historial y tendencias
    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    df_prev   = update_history(hist_path, total)
    trend     = compute_trends(df7, df_prev, topic_col, views_col) if not df_prev.empty else None

    # 4) Gráfico de distribución
    chart_path = os.path.join(out_dir, 'bar_topics.png')
    df7[topic_col].value_counts().plot.bar()
    plt.title('Artículos por tópico (últimos 7 días)')
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

    # 5) Construcción de narrativa automática
    md = []
    md.append(f"# Newsletter semanal ({datetime.now().date()})\n")
    # Datos básicos
    start = (datetime.now() - timedelta(days=7)).strftime('%d %b')
    end   = datetime.now().strftime('%d %b')
    md.append(f"**Total de artículos ({start} – {end}):** {total}  \n")
    md.append(f"**Tópicos cubiertos:** {df7[topic_col].nunique()}\n")
    md.append("---\n")

    # Hallazgos clave
    if trend is not None:
        prev_total = int(df_prev['total'].iloc[0])
        pct = (total - prev_total) / prev_total * 100
        sign = "+" if pct >= 0 else ""
        md.append("## 🏅 Hallazgos clave\n")
        md.append(f"- **Variación semanal:** {sign}{pct:.1f}% (de {prev_total} a {total} artículos).")
        
        # Top incremento y disminución
        gain = trend.sort_values('pct_change', ascending=False).iloc[0]
        loss = trend.sort_values('pct_change').iloc[0]
        md.append(f"- **Mayor incremento:** {gain.name} (+{gain['pct_change']:.0f}% notas).")
        md.append(f"- **Mayor disminución:** {loss.name} ({loss['pct_change']:.0f}% notas).")
        md.append("\n")
        
        # 📈 Variación por tópico
        md.append("### 📈 Variación por tópico\n")
        md.append("| Tópico | Anterior | Actual | Δ notas | % cambio |")
        md.append("|---|---:|---:|---:|---:|")
        for tema, row in trend.iterrows():
            ant   = int(row['previous'])
            act   = int(row['current'])
            delta = int(row['delta'])
            pct_t = row['pct_change']
            md.append(f"| {tema} | {ant} | {act} | {delta:+d} | {pct_t:+.1f}% |")
        md.append("")   # separador final

    
    # Distribución y KPI
    md.append("## 📊 Distribución por tópico\n")
    md.append(f"![Artículos por tópico]({os.path.basename(chart_path)})\n")
    md.append("\n---\n")
    md.append("## 🔝 Tópicos más frecuentes\n")
    md.append("| Tópico | Notas | % Total | Vistas | Vistas/Nota |")
    md.append("|---|---:|---:|---:|---:|")
    total_views = df7[views_col].sum()
    for tema, cnt in df7[topic_col].value_counts().head(8).items():
        views = df7[df7[topic_col] == tema][views_col].sum()
        md.append(f"| {tema} | {cnt} | {cnt/total*100:.0f}% | {views} | {views/cnt:.1f} |")
    md.append("\n---\n")

    # Artículos destacados
    md.append("## ✨ Artículos destacados\n")
    for _, r in df7.sort_values(date_col, ascending=False).head(3).iterrows():
        fecha = r[date_col].strftime('%d %b %Y')
        md.append(f"### {r[title_col]}\n*{fecha}*\n")
        if summary_col: md.append(r[summary_col] + "\n")
        if url_col:     md.append(f"[Leer más]({r[url_col]})\n")
    md.append("\n---\n")

    # Recomendaciones
    md.append("## 🔮 Recomendaciones\n")
    md.append("- Refuerzo en **Policial**: explotar el alto engagement con reportajes.")
    md.append("- Revitalizar **Salud**: infografías y entrevistas para aumentar interés.")
    md.append("- Optimizar **Internacional**: investigar causas de variación y ajustar enfoque.\n")

    # 6) Escritura final del Markdown
    out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))

    print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python newsletter.py <csv_path> <out_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
