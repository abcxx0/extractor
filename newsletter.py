#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os, sys, csv
from scipy.interpolate import make_interp_spline
import numpy as np


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
        # 1) Leemos el CSV y parseamos la columna ‘fecha’ como datetime
        hist = pd.read_csv(hist_path, parse_dates=['fecha'])
        # 2) Convertimos a date para descartar la hora
        hist['fecha'] = hist['fecha'].dt.date
    else:
        hist = pd.DataFrame(columns=['fecha','total'])

    # 3) Buscamos la fila de hace 7 días (ahora ambos son date)
    prev = hist[hist['fecha'] == (today - timedelta(days=7))]

    # 4) Añadimos la fila de hoy
    new_row = {'fecha': today, 'total': total}
    hist = pd.concat([hist, pd.DataFrame([new_row])], ignore_index=True)

    # 5) Guardamos sólo la parte de fecha (YYYY-MM-DD) para mantener el CSV limpio
    hist.to_csv(hist_path, index=False, date_format='%Y-%m-%d')

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

    # ——— Nuevas líneas para tendencias automáticas ———
    # Defino fecha de hoy y de hace 7 días
    today = datetime.now().date()
    prev_date = today - timedelta(days=7)

    # Intento leer el CSV de la semana anterior
    prev_file = os.path.join(out_dir, f"{prev_date}-articulos.csv")
    if os.path.exists(prev_file):
        df_prev_week = pd.read_csv(prev_file, parse_dates=[date_col])
    else:
        df_prev_week = pd.DataFrame(columns=df.columns)
    # ————————————————————————————————————————————


    # 3) Historial y tendencias
    os.makedirs(out_dir, exist_ok=True)
    hist_path = os.path.join(out_dir, 'historial.csv')
    
    # Historial de totales (sigue igual)
    prev_totals = update_history(hist_path, total)

    # Tendencias por tópico usando df_prev_week
    trend = compute_trends(df7, df_prev_week, topic_col, views_col) \
            if not df_prev_week.empty else None

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

        # Artículos destacados por vistas
    md.append("## ✨ Artículos destacados\n")
    for _, r in df7.sort_values(views_col, ascending=False).head(4).iterrows():
        fecha = r[date_col].strftime('%d %b %Y')
        vistas = int(r[views_col])
        md.append(f"### {r[title_col]}\n*{fecha} — {vistas} vistas*\n")
        if summary_col: md.append(r[summary_col] + "\n")
        if url_col:     md.append(f"[Leer más]({r[url_col]})\n")
    md.append("\n---\n")

           # Recomendaciones dinámicas basadas solo en esta semana
    md.append("## 🔮 Recomendaciones\n")
    recomendaciones = []

    resumen = (
        df7.groupby(topic_col)
           .agg(notas=('ID', 'count'), vistas_totales=(views_col, 'sum'))
           .assign(engagement=lambda x: x['vistas_totales'] / x['notas'])
    )

    # REFUERZO
    refuerzo = resumen[resumen['notas'] <= 3].sort_values('engagement', ascending=False).head(1)
    for tema, row in refuerzo.iterrows():
        recomendaciones.append(f"- Refuerzo en **{tema}**: alto interés con pocas notas (engagement: {row['engagement']:.1f}).")

    # OPTIMIZAR
    optimizar = resumen[resumen['notas'] >= 3].sort_values('engagement').head(1)
    for tema, row in optimizar.iterrows():
        recomendaciones.append(f"- Optimizar **{tema}**: bajo interés relativo pese a varias notas (engagement: {row['engagement']:.1f}).")

    # BUEN RENDIMIENTO
    buen_rend = resumen[(resumen['notas'] >= 3) & (resumen['engagement'] >= 2.5)]
    if not buen_rend.empty:
        top = buen_rend.sort_values('engagement', ascending=False).head(1)
        for tema, row in top.iterrows():
            recomendaciones.append(f"- Buen rendimiento en **{tema}**: mantener estrategia (engagement: {row['engagement']:.1f}).")

    if recomendaciones:
        md.extend(recomendaciones)
    else:
        md.append("- Esta semana no se detectaron patrones claros.\n")


    # Autores de la semana (solo nombres, orden informativo no numérico)
    md.append("\n## ✍️ Autores de la semana\n")
    autor_col = next((c for c in df7.columns if 'autor' in c.lower()), None)
    if autor_col:
        autores = (
            df7.groupby(autor_col)
               .agg(articulos=('ID', 'count'), vistas_totales=(views_col, 'sum'))
               .assign(orden=lambda x: x['articulos'] * 1.5 + x['vistas_totales'] / 10)
               .sort_values('orden', ascending=False)
               .head(5)
        )
        for autor in autores.index:
            md.append(f"- {autor}")
    else:
        md.append("- No se detectó una columna de autor.\n")


    # 📈 Gráfico de vistas acumuladas por día (curva suave)
df7['fecha_dia'] = df7[date_col].dt.date
vistas_por_dia = df7.groupby('fecha_dia')[views_col].sum().sort_index()

# Convertir fechas a números para suavizar
x = np.arange(len(vistas_por_dia))
y = vistas_por_dia.values
x_smooth = np.linspace(x.min(), x.max(), 300)

spl = make_interp_spline(x, y, k=2)
y_smooth = spl(x_smooth)

# Graficar curva
line_chart_path = os.path.join(out_dir, 'vistas_diarias.png')
plt.figure(figsize=(8, 4))
plt.plot(x_smooth, y_smooth, color='#5A78D1', linewidth=2.5)
plt.xticks(ticks=x, labels=vistas_por_dia.index.strftime('%d %b'), rotation=45)
plt.title('📈 Vistas acumuladas por día')
plt.xlabel('Fecha')
plt.ylabel('Vistas totales')
plt.grid(alpha=0.2)
plt.tight_layout()
plt.savefig(line_chart_path)
plt.close()

plt.close()

# Insertar en el markdown
md.append("## 📈 Vistas acumuladas por día\n")
md.append(f"![Vistas diarias]({os.path.basename(line_chart_path)})\n")

# 6) Escritura final del Markdown
out_md = os.path.join(out_dir, f"{datetime.now().date()}-newsletter.md")
with open(out_md, 'w', encoding='utf-8') as f:
    f.write("\n".join(md))

# ——— Guardar el detalle de esta semana para la próxima corrida ———
semana_path = os.path.join(out_dir, f"{today}-articulos.csv")
df7.to_csv(semana_path, index=False, date_format='%Y-%m-%d')

# Purga archivos de más de 7 días atrás
for fname in os.listdir(out_dir):
    if fname.endswith('-articulos.csv'):
        fecha_str = fname.split('-articulos.csv')[0]
        try:
            fecha = datetime.fromisoformat(fecha_str).date()
            if fecha < prev_date:
                os.remove(os.path.join(out_dir, fname))
        except ValueError:
            pass
# ————————————————————————————————————————————————

print(f"✅ Newsletter con análisis avanzado generada en {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python newsletter.py <csv_path> <out_dir>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
